import os
import sys
import shutil
import unittest
from pathlib import Path

from tempo_core import logger

import ue4ss_installer_core.ue4ss
import ue4ss_installer_core.file_io

import tempo_core.file_io
import tempo_core.settings
import tempo_core.main_logic
import tempo_core.programs.git
import tempo_core.initialization
import tempo_core.online_check
import tempo_core.manager

from tempo_binary_tool_manager import manager

CWD = Path.cwd()
TEMP_DIR = tempo_core.settings.get_temp_directory()

ZIP_STRS_TO_GAME_STRS = {
    "4_27_2_Shipping_Iostore_NoSigs.zip": "shipping_iostore_no_sigs_4_27_2",
    "4_27_2_Shipping_Iostore_Sigs.zip": "shipping_iostore_sigs_4_27_2",
    "4_27_2_Shipping_Loose_NoSigs.zip": "shipping_loose_no_sigs_4_27_2",
    "4_27_2_Shipping_Paks_NoSigs.zip": "shipping_paks_no_sigs_4_27_2",
    "4_27_2_Shipping_Paks_Sigs.zip": "shipping_paks_sigs_4_27_2",
    "5_1_1_Shipping_Iostore_NoSigs.zip": "shipping_iostore_no_sigs_5_1_1",
    "5_1_1_Shipping_Iostore_Sigs.zip": "shipping_iostore_sigs_5_1_1",
    "5_1_1_Shipping_Loose_NoSigs.zip": "shipping_loose_no_sigs_5_1_1",
    "5_1_1_Shipping_Paks_NoSigs.zip": "shipping_paks_no_sigs_5_1_1",
    "5_1_1_Shipping_Paks_Sigs.zip": "shipping_paks_sigs_5_1_1",
}

ZIP_STR = "4_27_2_Shipping_Iostore_NoSigs.zip"
GAME_STR = "shipping_iostore_no_sigs_4_27_2"


TESTS_DIR = Path(f"{TEMP_DIR}/tests")
GAME_SPECIFIC_TEST_DIR = Path(f"{TESTS_DIR}/{GAME_STR}")
GAME_DIR = Path(f"{GAME_SPECIFIC_TEST_DIR}/packaged_game")
GAME_INNER_EXE_DIR = Path(f"{GAME_SPECIFIC_TEST_DIR}/packaged_game/TempoTesting/Binaries/Win64")
GAME_INNER_EXE = Path(f"{GAME_INNER_EXE_DIR}/TempoTesting-Win64-Shipping.exe")
BASE_FILES_DIR = Path(f"{GAME_SPECIFIC_TEST_DIR}/base_files")
OUTPUT_DIR = Path(f"{GAME_SPECIFIC_TEST_DIR}/output")
UPROJECT_DIR = Path(f"{GAME_SPECIFIC_TEST_DIR}/unreal_project")
UPROJECT_CONTENT_DIR = Path(f"{UPROJECT_DIR}/Content")
UPROJECT_CONFIG_DIR = Path(f"{UPROJECT_DIR}/Config")
UPROJECT_FILE = Path(f"{UPROJECT_DIR}/TempoTesting.uproject")

logger.log_message(f'uproject_file: {UPROJECT_FILE}')


OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
GAME_DIR.mkdir(parents=True, exist_ok=True)
BASE_FILES_DIR.mkdir(parents=True, exist_ok=True)
UPROJECT_CONTENT_DIR.mkdir(parents=True, exist_ok=True)
UPROJECT_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
GAME_SPECIFIC_TEST_DIR.mkdir(parents=True, exist_ok=True)

SETTINGS_FILE = Path(f"{CWD}/tests/{GAME_STR}_tempo.json")


def cache_files() -> list[Path]:
    tests_cache_dir = Path(f"{tempo_core.manager.tools_cache.get_cache_dir()}/testing")
    ue4ss_zip_cache_dir = Path(f"{tests_cache_dir}/ue4ss_zip")
    packaged_games_cache_dir = Path(f"{tests_cache_dir}/packaged_games")
    uproject_files_cache_dir = Path(f"{tests_cache_dir}/uproject_files")

    tests_cache_dir.mkdir(parents=True, exist_ok=True)
    packaged_games_cache_dir.mkdir(parents=True, exist_ok=True)
    uproject_files_cache_dir.mkdir(parents=True, exist_ok=True)
    ue4ss_zip_cache_dir.mkdir(parents=True, exist_ok=True)

    for game_zip in ZIP_STRS_TO_GAME_STRS.keys():
        game_url = f"https://github.com/Tempo-Organization/tempo-games/releases/download/1.0.0/{game_zip}"
        zip_path = Path(f"{packaged_games_cache_dir}/{game_zip}")
        # add some verification to make sure the zip was valid here
        if not zip_path.is_file():
            logger.log_message("the following game zip is being downloaded/cached. Please wait...")
            tempo_core.file_io.download_file(game_url, zip_path)

    template_files = [
        "Uprojects/4_11_2/ReusableMods/Content/Mods/LooseExampleMod/ModActor.uasset",
        "Uprojects/4_11_2/ReusableMods/Content/Mods/RepakMadeExampleMod/ModActor.uasset",
        "Uprojects/4_11_2/ReusableMods/Content/Mods/UnrealPakMadeExampleMod/ModActor.uasset",
        "Uprojects/4_27_2/ReusableMods/Content/Mods/MaterialTest/ModActor.uasset",
        "Uprojects/4_27_2/ReusableMods/Content/Mods/MaterialTest/DA_MaterialTest.uasset",
        "Uprojects/4_27_2/ReusableMods/Content/Mods/MaterialTest/ModRoot/Materials/M_MaterialTest.uasset",
        "Uprojects/4_27_2/ReusableMods/Content/Mods/EngineMadeExampleMod/DA_EngineMadeExampleMod.uasset",
        "Uprojects/4_27_2/ReusableMods/Content/Mods/EngineMadeExampleMod/ModActor.uasset",
        "Uprojects/4_27_2/ReusableMods/Content/Mods/EngineMadeExampleMod/ModRoot/Blueprints/BP_PlaceHolder.uasset",
        "Uprojects/4_27_2/ReusableMods/Content/Mods/RetocMadeExampleMod/ModActor.uasset",
    ]

    for template_file in template_files:
        if not Path(f"{uproject_files_cache_dir}/{template_file}").is_file():
            tempo_core.programs.git.download_files_from_github_repo(
                repo_url="https://github.com/Tempo-Organization/tempo-tests",
                repo_branch="main",
                file_paths=[template_file],
                output_directory=uproject_files_cache_dir,
            )
    return [uproject_files_cache_dir, packaged_games_cache_dir, ue4ss_zip_cache_dir]


def init_tempo_core() -> None:
    logger.log_message("started tempo core init")
    sys.argv.append("--settings_json")
    sys.argv.append(str(SETTINGS_FILE))

    sys.argv.append("--logs_directory")
    sys.argv.append((f"{TEMP_DIR}/logs"))

    tempo_core.main_logic.generate_uproject(
        project_file=UPROJECT_FILE, ignore_safety_checks=True,
    )

    tempo_core.initialization.initialization()

    tempo_core.main_logic.generate_uproject(
        project_file=UPROJECT_FILE, ignore_safety_checks=True,
    )


def copy_files_from_cache(cache_info: list[Path]) -> None:
    shutil.copytree(
        Path(cache_info[0] / 'Uprojects/4_11_2/ReusableMods/Content'),
        UPROJECT_CONTENT_DIR,
        dirs_exist_ok=True,
    )

    shutil.copytree(
        Path(cache_info[0] / 'Uprojects/4_27_2/ReusableMods/Content'),
        UPROJECT_CONTENT_DIR,
        dirs_exist_ok=True,
    )

    tempo_core.file_io.unzip_zip(
        zip_path=Path(f"{cache_info[1]}/{ZIP_STR}"),
        output_location=GAME_DIR,
    )


def init_tests() -> list[Path]:
    init_tempo_core()

    cache_info = cache_files()
    copy_files_from_cache(cache_info)
    return cache_info


def install_ue4ss(cache_dir: Path, game_exe_directory: Path) -> None:
    ue4ss_zip_path = Path(f"{cache_dir}/ue4ss.zip")

    if not ue4ss_zip_path.is_file():
        if not tempo_core.online_check.is_online:
            raise RuntimeError('You do not have ue4ss downloaded to cache, and cannot download because you are not connected to the web.')

        logger.log_message("started caching ue4ss release info")
        ue4ss_installer_core.ue4ss.cache_repo_releases_info("UE4SS-RE", "RE-UE4SS")
        logger.log_message("finished caching ue4ss release info")
        tag = ue4ss_installer_core.ue4ss.get_default_ue4ss_version_tag()
        file_names_to_download_links = (
            ue4ss_installer_core.ue4ss.get_file_name_to_download_links_from_tag(tag)
        )

        final_download_link = next(
            (
                link
                for link in file_names_to_download_links.values()
                if "ue4ss" in link.lower() and "zdev" not in link.lower()
            ),
            None,
        )
        if not final_download_link:
            raise RuntimeError(
                f'Unable to find a compatible UE4SS release for tag "{tag}"',
            )

        ue4ss_installer_core.file_io.download_file(
            final_download_link,
            Path(f"{cache_dir}/ue4ss.zip"),
        )

    ue4ss_installer_core.file_io.unzip_zip(
        ue4ss_zip_path, Path(game_exe_directory),
    )


class TestShippingIostoreNoSigsUE4(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        shutil.rmtree(TEMP_DIR)
        cache_info = init_tests()
        install_ue4ss(cache_info[2], GAME_INNER_EXE_DIR)
        UPROJECT_CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    # def tearDown(self):
    #     return super().tearDown()

    # def setUp(self):
    #     return

    # def test_0001_repak(self):
    #     tempo_core.main_logic.full_run(
    #         input_mod_names=["RepakMadeExampleMod"],
    #         toggle_engine=False,
    #         base_files_directory=BASE_FILES_DIR,
    #         output_directory=OUTPUT_DIR,
    #         use_symlinks=False,
    #     )

    # def test_0002_unreal_pak(self):
    #     # check full run all works, and test mods all works eventually
    #     # tempo_core.main_logic.test_mods(
    #     #     input_mod_names=["UnrealPakMadeExampleMod"],
    #     #     toggle_engine=False,
    #     #     use_symlinks=False,
    #     # )
    #     tempo_core.main_logic.full_run(
    #         input_mod_names=["UnrealPakMadeExampleMod"],
    #         toggle_engine=False,
    #         base_files_directory=BASE_FILES_DIR,
    #         output_directory=OUTPUT_DIR,
    #         use_symlinks=False,
    #     )

    # def test_0003_engine_made(self):
    #     tempo_core.main_logic.full_run(
    #         input_mod_names=["EngineMadeExampleMod"],
    #         toggle_engine=False,
    #         base_files_directory=BASE_FILES_DIR,
    #         output_directory=OUTPUT_DIR,
    #         use_symlinks=False,
    #     )

    # def test_0004_loose(self):
    #     tempo_core.main_logic.full_run(
    #         input_mod_names=["LooseExampleMod"],
    #         toggle_engine=False,
    #         base_files_directory=BASE_FILES_DIR,
    #         output_directory=OUTPUT_DIR,
    #         use_symlinks=False,
    #     )

    # def test_0005_material_test(self):
    #     tempo_core.main_logic.full_run(
    #         input_mod_names=["MaterialTest"],
    #         toggle_engine=False,
    #         base_files_directory=BASE_FILES_DIR,
    #         output_directory=OUTPUT_DIR,
    #         use_symlinks=False,
    #     )

    # def test_0006_retoc(self) -> None:
    #     tempo_core.main_logic.full_run(
    #         input_mod_names=["RetocMadeExampleMod"],
    #         toggle_engine=False,
    #         base_files_directory=BASE_FILES_DIR,
    #         output_directory=OUTPUT_DIR,
    #         use_symlinks=False,
    #     )

    def test_0007_all(self) -> None:
        tempo_core.main_logic.full_run_all(
            toggle_engine=False,
            base_files_directory=BASE_FILES_DIR,
            output_directory=OUTPUT_DIR,
            use_symlinks=False,
        )

    # def test_0007_all(self):
    #     tempo_core.main_logic.test_mods_all(
    #         toggle_engine=False,
    #         use_symlinks=False
    #     )


if __name__ == "__main__":
    unittest.main()

# To Do
#
# add_mod command auto does "pak_dir_structure": "C:\\Users\\mods" for some reason
#
# currently retoc isn't generating a release zip for some reason
#
# timers are not running for every command, for example the build command
#
# optional ue4ss tag specification
# have it install ue4ss into each game, and cache these installs, does it hash verify currently, and ensure valid zip?
# after releases are made unzip them into the game?
# check the files all exist at the right place, and are appropriate sizes
# add a potential check for if the above is taking too long
# retoc and unreal pak example made mods are not being packaged into releases dir properly
# check that the file includes are tested during testing
# if using iostore unreal pak made stuff, it either doesn't make a pak if there
# are not files that go in paks avialabnle or it needs to be a sep step

# Later
# account for bp only games/ones that have the exe within the Engine dir tree
# make all uprojects for each game version
# make all tempo configs for each game version


# Other:
# sometimes cache zips can get corrupted, for example interrupted mid download, deal with this, maybe add a hash check
# fix add/remove/edit mod cli functions/add questionary versions
# make params use one-two instead of one_two
# commandline thing to fix retoc miosing uproject name
# command for uassetgui to fix retoc missing uproject name for unreal engine 4 versions
# # choose what parts go where doc wise, tempo-[cli, tempo-[core, tempo-gui, in editor, etc...
# update documentation




















# Later
# paths to executables in the hook state stuff, should deal with resolving relative paths and absolute paths
# giving projects ids to env vars can be grabbed via id and other stuff?
# add a global config, you can place various things to be reused by other configs here
# like one global config for all your unreal engine installs
# switch to pathlib instead of strings for a lot of things
# make unique cache/temp dir enums?
# ability to set unreal version through commandline, and env var on top of the auto detection based on game, and settings file
# -nullrhi compatibility
# toggle option for the enable= for mods, right now upon running the tool it will delete the files if they exist when not enabled


# saw the below on 5.6, Ghost, spongebob titans of the tide
# LogCook: Display: FULL COOK: Neither -legacyiterative nor -cookincremental were specified. Deleting previously cooked
# packages for platform Windows and recooking all packages discovered in the current cook.
# refine timers eventually
#
