import os
import sys
import shutil
import pathlib
import unittest

import ue4ss_installer_gui.ue4ss
import ue4ss_installer_gui.file_io

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

import src.tempo_core.cache
import src.tempo_core.file_io
import src.tempo_core.settings
import src.tempo_core.main_logic
import src.tempo_core.programs.git
import src.tempo_core.initialization


CWD = os.getcwd()
TEMP_DIR = src.tempo_core.settings.get_temp_directory()

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


TESTS_DIR = os.path.normpath(f"{TEMP_DIR}/tests")
GAME_SPECIFIC_TEST_DIR = os.path.normpath(f"{TESTS_DIR}/{GAME_STR}")
GAME_DIR = os.path.normpath(f"{GAME_SPECIFIC_TEST_DIR}/packaged_game")
GAME_INNER_EXE_DIR = os.path.normpath(
    f"{GAME_SPECIFIC_TEST_DIR}/packaged_game/TempoTesting/Binaries/Win64"
)
GAME_INNER_EXE = os.path.normpath(
    f"{GAME_INNER_EXE_DIR}/TempoTesting-Win64-Shipping.exe"
)
BASE_FILES_DIR = os.path.normpath(f"{GAME_SPECIFIC_TEST_DIR}/base_files")
OUTPUT_DIR = os.path.normpath(f"{GAME_SPECIFIC_TEST_DIR}/output")
UPROJECT_DIR = os.path.normpath(f"{GAME_SPECIFIC_TEST_DIR}/unreal_project")
UPROJECT_CONTENT_DIR = os.path.normpath(f"{UPROJECT_DIR}/Content")
UPROJECT_CONFIG_DIR = os.path.normpath(f"{UPROJECT_DIR}/Config")
UPROJECT_FILE = os.path.normpath(f"{UPROJECT_DIR}/TempoTesting.uproject")


os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(GAME_DIR, exist_ok=True)
os.makedirs(BASE_FILES_DIR, exist_ok=True)
os.makedirs(UPROJECT_CONTENT_DIR, exist_ok=True)
os.makedirs(UPROJECT_CONFIG_DIR, exist_ok=True)
os.makedirs(GAME_SPECIFIC_TEST_DIR, exist_ok=True)

SETTINGS_FILE = os.path.normpath(f"{CWD}/tests/{GAME_STR}_tempo.json")


def cache_files() -> list[str]:
    TEMPO_CACHE_DIR = src.tempo_core.cache.get_cache_dir()
    TESTS_CACHE_DIR = os.path.normpath(f"{TEMPO_CACHE_DIR}/testing")
    UE4SS_ZIP_CACHE_DIR = os.path.normpath(f"{TESTS_CACHE_DIR}/ue4ss_zip")
    PACKAGED_GAMES_CACHE_DIR = os.path.normpath(f"{TESTS_CACHE_DIR}/packaged_games")
    UPROJECT_FILES_CACHE_DIR = os.path.normpath(f"{TESTS_CACHE_DIR}/uproject_files")

    os.makedirs(TESTS_CACHE_DIR, exist_ok=True)
    os.makedirs(PACKAGED_GAMES_CACHE_DIR, exist_ok=True)
    os.makedirs(UPROJECT_FILES_CACHE_DIR, exist_ok=True)
    os.makedirs(UE4SS_ZIP_CACHE_DIR, exist_ok=True)

    for game_zip in ZIP_STRS_TO_GAME_STRS.keys():
        game_url = f"https://github.com/Tempo-Organization/tempo-games/releases/download/1.0.0/{game_zip}"
        zip_path = os.path.normpath(f"{PACKAGED_GAMES_CACHE_DIR}/{game_zip}")
        # add some verification to make sure the zip was valid here
        if not os.path.isfile(zip_path):
            print("the following game zip is being downloaded/cached. Please wait...")
            src.tempo_core.file_io.download_file(game_url, zip_path)

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
        if not os.path.isfile(
            os.path.normpath(f"{UPROJECT_FILES_CACHE_DIR}/{template_file}")
        ):
            src.tempo_core.programs.git.download_files_from_github_repo(
                repo_url="https://github.com/Tempo-Organization/tempo-tests",
                repo_branch="main",
                file_paths=[template_file],
                output_directory=UPROJECT_FILES_CACHE_DIR,
            )
    return [UPROJECT_FILES_CACHE_DIR, PACKAGED_GAMES_CACHE_DIR, UE4SS_ZIP_CACHE_DIR]


def init_tempo_core():
    print("started tempo core init")
    sys.argv.append("--settings_json")
    sys.argv.append(SETTINGS_FILE)

    sys.argv.append("--logs_directory")
    sys.argv.append(os.path.normpath(f"{TEMP_DIR}/logs"))

    src.tempo_core.main_logic.generate_uproject(
        project_file=UPROJECT_FILE, ignore_safety_checks=True
    )

    src.tempo_core.initialization.initialization()
    print("finished tempo core init")

    # we run this twice, as init checks the uproject exists, but also deletes the temp directory
    # src.tempo_core.main_logic.generate_uproject(
    #     project_file=UPROJECT_FILE, ignore_safety_checks=True
    # )


def copy_files_from_cache(cache_info):
    shutil.copytree(
        os.path.normpath(f"{cache_info[0]}/Uprojects/4_11_2/ReusableMods/Content"),
        UPROJECT_CONTENT_DIR,
        dirs_exist_ok=True,
    )

    shutil.copytree(
        os.path.normpath(f"{cache_info[0]}/Uprojects/4_27_2/ReusableMods/Content"),
        UPROJECT_CONTENT_DIR,
        dirs_exist_ok=True,
    )

    src.tempo_core.file_io.unzip_zip(
        zip_path=os.path.normpath(f"{cache_info[1]}/{ZIP_STR}"),
        output_location=GAME_DIR,
    )


def tests_init() -> list[str]:
    init_tempo_core()
    cache_info = cache_files()
    copy_files_from_cache(cache_info)
    return cache_info


def install_ue4ss(cache_dir: str, game_exe_directory: str):
    ue4ss_zip_path = pathlib.Path(f"{cache_dir}/ue4ss.zip")

    if not ue4ss_zip_path.exists():
        print("started caching ue4ss release info")
        ue4ss_installer_gui.ue4ss.cache_repo_releases_info("UE4SS-RE", "RE-UE4SS")
        print("finished caching ue4ss release info")
        tag = ue4ss_installer_gui.ue4ss.get_default_ue4ss_version_tag()
        file_names_to_download_links = (
            ue4ss_installer_gui.ue4ss.get_file_name_to_download_links_from_tag(tag)
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
                f'Unable to find a compatible UE4SS release for tag "{tag}"'
            )

        ue4ss_installer_gui.file_io.download_file(
            final_download_link,
            os.path.normpath(f"{cache_dir}/ue4ss.zip"),
        )

    ue4ss_installer_gui.file_io.unzip_zip(
        ue4ss_zip_path, pathlib.Path(game_exe_directory)
    )


class TestShippingIostoreNoSigsUE4(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        shutil.rmtree(TEMP_DIR)
        cache_info = tests_init()
        install_ue4ss(cache_info[2], GAME_INNER_EXE_DIR)

    # def tearDown(self):
    #     return super().tearDown()

    # def setUp(self):
    #     return

    # def test_0001_repak(self):
    #     src.tempo_core.main_logic.full_run(
    #         input_mod_names=["RepakMadeExampleMod"],
    #         toggle_engine=False,
    #         base_files_directory=BASE_FILES_DIR,
    #         output_directory=OUTPUT_DIR,
    #         use_symlinks=False,
    #     )

    def test_0002_unreal_pak(self):
        # check full run all works, and test mods all works eventually
        src.tempo_core.main_logic.test_mods(
            input_mod_names=["UnrealPakMadeExampleMod"],
            toggle_engine=False,
            use_symlinks=False,
        )
        # src.tempo_core.main_logic.full_run(
        #     input_mod_names=["UnrealPakMadeExampleMod"],
        #     toggle_engine=False,
        #     base_files_directory=BASE_FILES_DIR,
        #     output_directory=OUTPUT_DIR,
        #     use_symlinks=False,
        # )

    # def test_0003_engine_made(self):
    #     src.tempo_core.main_logic.full_run(
    #         input_mod_names=["EngineMadeExampleMod"],
    #         toggle_engine=False,
    #         base_files_directory=BASE_FILES_DIR,
    #         output_directory=OUTPUT_DIR,
    #         use_symlinks=False,
    #     )

    # def test_0004_loose(self):
    #     src.tempo_core.main_logic.full_run(
    #         input_mod_names=["LooseExampleMod"],
    #         toggle_engine=False,
    #         base_files_directory=BASE_FILES_DIR,
    #         output_directory=OUTPUT_DIR,
    #         use_symlinks=False,
    #     )

    # def test_0005_material_test(self):
    #     src.tempo_core.main_logic.full_run(
    #         input_mod_names=["MaterialTest"],
    #         toggle_engine=False,
    #         base_files_directory=BASE_FILES_DIR,
    #         output_directory=OUTPUT_DIR,
    #         use_symlinks=False,
    #     )

    # def test_0006_retoc(self):
    #     src.tempo_core.main_logic.full_run(
    #         input_mod_names=["RetocMadeExampleMod"],
    #         toggle_engine=False,
    #         base_files_directory=BASE_FILES_DIR,
    #         output_directory=OUTPUT_DIR,
    #         use_symlinks=False,
    #     )

    # def test_0007_all(self):
    #     src.tempo_core.main_logic.full_run_all(
    #         toggle_engine=False,
    #         base_files_directory=BASE_FILES_DIR,
    #         output_directory=OUTPUT_DIR,
    #         use_symlinks=False
    #     )

    # def test_0007_all(self):
    #     src.tempo_core.main_logic.test_mods_all(
    #         toggle_engine=False,
    #         use_symlinks=False
    #     )


if __name__ == "__main__":
    unittest.main()


# To Do
# have it install ue4ss into each game, and cache these installs
# after releases are made unzip them into the game
# check the files all exist at the right place, and are appropriate sizes
# run the game with nullrhi parameter, and parse the ue4ss log for mod output
# add a potential check for if the above is taking too long
# retoc and unreal pak example made mods are not being packaged into releases dir properly

# make all uprojects for each game version
# make all tempo configs for each game version
# check that the file includes are tested during testing
# currently retoc isn't generating a release zip for some reason
# engine packed material test mod only has pak file and not all 3 files for some reason

# Later
# account for bp only games/ones that have the exe within the Engine dir tree
# relative paths in config and all are broken right now, test without and figure it out later

# Maybes:
# make unique cache/temp dir enums?

# if using iostore unreal pak made stuff, it either doesn't make a pak if there
# are not files that go in paks avialabnle or it needs to be a sep step
