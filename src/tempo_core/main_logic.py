import json
import os
import shutil
import subprocess
import sys
from pathlib import Path, PurePath
from typing import TypeAlias

from tempo_core import (
    app_runner,
    data_structures,
    engine,
    file_io,
    game_runner,
    hook_states,
    logger,
    packing,
    process_management,
    settings,
    utilities,
    online_check,
    manager,
)
from tempo_core.programs import unreal_engine
from tempo_core.threads import constant, game_monitor

from tempo_binary_tools import spaghetti, stove, uasset_gui, umodel, fmodel, kismet_analyzer


@hook_states.hook_state_decorator(
    start_hook_state_type=data_structures.HookStateType.INIT,
)
def init_thread_system() -> None:
    constant.constant_thread()


def close_thread_system() -> None:
    constant.stop_constant_thread()


# all things below this should be functions that correspond to cli logic


def generate_mods_other(*, use_symlinks: bool) -> None:
    packing.cooking()
    packing.generate_mods(use_symlinks=use_symlinks)
    game_runner.run_game()
    game_monitor.game_monitor_thread()


def test_mods(*, input_mod_names: list[str], toggle_engine: bool, use_symlinks: bool) -> None:
    if toggle_engine:
        engine.toggle_engine_off()
    for mod_name in input_mod_names:
        settings.settings_information.mod_names.append(mod_name)
    generate_mods_other(use_symlinks=use_symlinks)
    if toggle_engine:
        engine.toggle_engine_on()


def test_mods_all(*, toggle_engine: bool, use_symlinks: bool) -> None:
    if toggle_engine:
        engine.toggle_engine_off()
    mod_info_dict = settings.settings_information.settings.get("mods_info", {})
    for name in mod_info_dict.keys():
        if name not in settings.settings_information.mod_names:
            settings.settings_information.mod_names.append(name)
    generate_mods_other(use_symlinks=use_symlinks)
    if toggle_engine:
        engine.toggle_engine_on()


def full_run(
    *,
    input_mod_names: list[str],
    toggle_engine: bool,
    base_files_directory: Path,
    output_directory: Path,
    use_symlinks: bool,
) -> None:
    if toggle_engine:
        engine.toggle_engine_off()
    for mod_name in input_mod_names:
        settings.settings_information.mod_names.append(mod_name)
    packing.cooking()
    generate_mods(input_mod_names=input_mod_names, use_symlinks=use_symlinks)
    generate_mod_releases(
        mod_names=input_mod_names,
        base_files_directory=base_files_directory,
        output_directory=output_directory,
    )
    if toggle_engine:
        engine.toggle_engine_on()


def full_run_all(
    *,
    toggle_engine: bool,
    base_files_directory: Path,
    output_directory: Path,
    use_symlinks: bool,
) -> None:
    if toggle_engine:
        engine.toggle_engine_off()
    mods_info = settings.settings_information.settings.get("mods_info", {})
    for key in mods_info.keys():
        settings.settings_information.mod_names.append(key)
    packing.cooking()
    generate_mods_all(use_symlinks=use_symlinks)
    generate_mod_releases_all(
        base_files_directory=base_files_directory, output_directory=output_directory,
    )
    if toggle_engine:
        engine.toggle_engine_on()


def install_spaghetti(run_after_install: bool) -> None:
    tool_info = spaghetti.SpaghettiToolInfo(cache=manager.tools_cache)
    tool_info.ensure_tool_installed()
    tool_path = tool_info.get_executable_path()
    if run_after_install:
        app_runner.run_app(tool_path)


def install_stove(run_after_install: bool) -> None:
    tool_info = stove.StoveToolInfo(cache=manager.tools_cache)
    tool_info.ensure_tool_installed()
    tool_path = tool_info.get_executable_path()
    if run_after_install:
        app_runner.run_app(tool_path)


def install_kismet_analyzer(run_after_install: bool) -> None:
    tool_info = kismet_analyzer.KismetAnalyzerToolInfo(cache=manager.tools_cache)
    tool_info.ensure_tool_installed()
    tool_path = tool_info.get_executable_path()
    if run_after_install:
        subprocess.Popen(
            f'start cmd /k "{tool_path}"" -h',
            shell=True,
            cwd=tool_path.parent,
        )


def install_uasset_gui(run_after_install: bool) -> None:
    tool_info = uasset_gui.UassetGuiToolInfo(cache=manager.tools_cache)
    tool_info.ensure_tool_installed()
    tool_path = tool_info.get_executable_path()
    if run_after_install:
        app_runner.run_app(tool_path)


def open_latest_log() -> None:
    file_to_open = Path(f"{logger.log_information.log_base_dir}/{logger.log_information.log_prefix}_latest.log")
    file_io.open_file_in_default(file_to_open)


def run_game(*, toggle_engine: bool) -> None:
    if toggle_engine:
        engine.toggle_engine_off()
    game_runner.run_game()
    game_monitor.game_monitor_thread()
    if toggle_engine:
        engine.toggle_engine_on()


def close_game() -> None:
    game_exe_path = settings.get_game_exe_path()
    if not game_exe_path:
        raise FileNotFoundError("cannot find game exe")
    process_management.kill_process(game_exe_path.name)


def run_engine() -> None:
    engine.open_game_engine()


def close_engine() -> None:
    engine.close_game_engine()


def install_umodel(run_after_install: bool) -> None:
    tool_info = umodel.UmodelToolInfo(cache=manager.tools_cache)
    tool_info.ensure_tool_installed()
    tool_path = tool_info.get_executable_path()
    if run_after_install:
        app_runner.run_app(tool_path)


def install_fmodel(run_after_install: bool) -> None:
    tool_info = fmodel.FmodelToolInfo(cache=manager.tools_cache)
    tool_info.ensure_tool_installed()
    tool_path = tool_info.get_executable_path()
    if run_after_install:
        app_runner.run_app(tool_path)


def get_solo_build_project_command() -> str:
    command = (
        f'"Engine\\Build\\BatchFiles\\RunUAT.{file_io.get_platform_wrapper_extension()}" {settings.get_unreal_engine_building_main_command()} '
        f'-project="{settings.get_uproject_file()}" '
    )
    for arg in settings.get_engine_building_args():
        command = f"{command} {arg}"
    return command


def run_proj_build_command(command: str) -> None:
    command_parts = command.split(" ")
    executable = Path(command_parts[0])
    args = command_parts[1:]
    unreal_engine_dir = settings.get_unreal_engine_dir()
    if not unreal_engine_dir:
        raise RuntimeError('Unreal engine install was not valid.')
    app_runner.run_app(
        exe_path=executable, args=args, working_dir=unreal_engine_dir,
    )


def build(*, toggle_engine: bool) -> None:
    if toggle_engine:
        engine.toggle_engine_off()
    logger.log_message("Project Building Starting")
    run_proj_build_command(get_solo_build_project_command())
    logger.log_message("Project Building Complete")
    if toggle_engine:
        engine.toggle_engine_on()


def upload_changes_to_repo() -> None:
    if not online_check.is_online:
        raise RuntimeError('You are not able to upload changes to repos when not connected to the web.')
    repo_path = settings.settings_information.settings["git_info"]["repo_path"]
    branch = settings.settings_information.settings["git_info"]["repo_branch"]
    desc = input("Enter commit description: ")
    git_path = shutil.which("git")
    if git_path is None:
        raise FileNotFoundError(
            "Git executable not found. Ensure it's installed and in your system PATH.",
        )

    status_result = subprocess.run(
        [git_path, "status", "--porcelain"],
        capture_output=True,
        text=True,
        cwd=repo_path,
        check=False,
    )
    if status_result.returncode != 0 or not status_result.stdout.strip():
        logger.log_message("No changes detected or not in a Git repository.")
        sys.exit(1)

    checkout_result = subprocess.run(
        [git_path, "checkout", branch],
        capture_output=True,
        text=True,
        cwd=repo_path,
        check=False,
    )
    if checkout_result.returncode != 0:
        logger.log_message(f"Failed to switch to the {branch} branch.")
        sys.exit(1)

    subprocess.run([git_path, "add", "."], check=True, cwd=repo_path)

    commit_result = subprocess.run(
        [git_path, "commit", "-m", desc],
        capture_output=True,
        text=True,
        cwd=repo_path,
        check=False,
    )
    if commit_result.returncode != 0:
        logger.log_message("Commit failed.")
        sys.exit(1)

    push_result = subprocess.run(
        [git_path, "push", "origin", branch],
        capture_output=True,
        text=True,
        cwd=repo_path,
        check=False,
    )
    if push_result.returncode != 0:
        logger.log_message("Push failed.")
        sys.exit(1)

    logger.log_message("Changes committed and pushed successfully.")


def enable_mods(settings_json: Path, mod_names: list) -> None:
    try:
        with settings_json.open(encoding="utf-8") as file:
            settings = json.load(file)

        mods_enabled = False

        mods_info = settings.get("mods_info", {})
        for mod_name in mods_info:
            if mod_name in mod_names:
                if not mods_info[mod_name]["is_enabled"]:
                    mods_info[mod_name]["is_enabled"] = True
                    mods_enabled = True
                    logger.log_message(f"Mod '{mod_name}' has been enabled.")
                else:
                    logger.log_message(f"Mod '{mod_name}' is already enabled.")

        if mods_enabled:
            updated_json_str = json.dumps(
                settings, indent=4, ensure_ascii=False, separators=(",", ": "),
            )

            with settings_json.open("w", encoding="utf-8") as file:
                file.write(updated_json_str)

            logger.log_message(f"Mods successfully enabled in '{settings_json}'.")
        else:
            logger.log_message(
                "No mods were enabled because all specified mods were already enabled.",
            )

    except json.JSONDecodeError:
        logger.log_message(
            f"Error decoding JSON from file '{settings_json}'. Please check the file format.",
        )


def disable_mods(settings_json: Path, mod_names: list) -> None:
    try:
        with settings_json.open(encoding="utf-8") as file:
            settings = json.load(file)

        mods_disabled = False

        mods_info = settings.get("mods_info", {})

        for mod_name in mods_info.keys():
            if mod_name in mod_names:
                if mods_info[mod_name]["is_enabled"]:
                    mods_info[mod_name]["is_enabled"] = False
                    mods_disabled = True
                    logger.log_message(f"Mod '{mod_name}' has been disabled.")
                else:
                    logger.log_message(f"Mod '{mod_name}' is already disabled.")

        if mods_disabled:
            updated_json_str = json.dumps(
                settings, indent=4, ensure_ascii=False, separators=(",", ": "),
            )

            with settings_json.open("w", encoding="utf-8") as file:
                file.write(updated_json_str)

            logger.log_message(f"Mods successfully disabled in '{settings_json}'.")
        else:
            logger.log_message(
                "No mods were disabled because all specified mods were already disabled.",
            )

    except json.JSONDecodeError:
        logger.log_message(
            f"Error decoding JSON from file '{settings_json}'. Please check the file format.",
        )


def add_mod(
    *,
    settings_json: Path,
    mod_name: str,
    packing_type: str,
    pak_dir_structure: str,
    mod_name_dir_type: str,
    mod_name_dir_name_override: str | None,
    pak_chunk_num: int | None,
    compression_type: str | None,
    is_enabled: bool,
    asset_paths: list,
    tree_paths: list,
) -> None:
    try:
        with settings_json.open() as file:
            settings = json.load(file)

        if "mods_info" not in settings or not isinstance(settings["mods_info"], dict):
            settings["mods_info"] = {}

        mod_data = {
            "pak_dir_structure": pak_dir_structure,
            "mod_name_dir_type": mod_name_dir_type,
            "mod_name_dir_name_override": mod_name_dir_name_override,
            "pak_chunk_num": pak_chunk_num,
            "packing_type": packing_type,
            "compression_type": compression_type,
            "is_enabled": is_enabled,
            "file_includes": {
                "asset_paths": asset_paths,
                "tree_paths": tree_paths,
            },
        }

        # def remove_none_values(data):
        #     if isinstance(data, dict):
        #         return {
        #             key: remove_none_values(value)
        #             for key, value in data.items()
        #             if value is not None
        #         }
        #     elif isinstance(data, list):
        #         return [
        #             remove_none_values(item)
        #             for item in data
        #             if item is not None
        #         ]
        #     else:
        #         return data

        JSONLike: TypeAlias = (
            dict[str, "JSONLike"]
            | list["JSONLike"]
            | str
            | int
            | float
            | bool
            | None
        )

        def remove_none_values(data: JSONLike) -> JSONLike:
            if isinstance(data, dict):
                return {
                    key: remove_none_values(value)
                    for key, value in data.items()
                    if value is not None
                }
            elif isinstance(data, list):
                return [
                    remove_none_values(item)
                    for item in data
                    if item is not None
                ]
            else:
                return data

        mod_data = remove_none_values(mod_data)

        if mod_name in settings["mods_info"]:
            logger.log_message(f"Mod '{mod_name}' already exists. Updating its data.")

        settings["mods_info"][mod_name] = mod_data

        with settings_json.open("w") as file:
            json.dump(settings, file, indent=4)

        logger.log_message(
            f"Mod '{mod_name}' successfully added/updated in '{settings_json}'.",
        )

    except json.JSONDecodeError:
        logger.log_message(
            f"Error decoding JSON from file '{settings_json}'. Please check the file format.",
        )


def remove_mods(settings_json: Path, mod_names: list) -> None:
    try:
        with settings_json.open(encoding="utf-8") as file:
            settings = json.load(file)

        mods_info = settings.get("mods_info", {})

        if not isinstance(mods_info, dict):
            logger.log_message(
                "Invalid mods_info format. Expected a dictionary keyed by mod name.",
            )
            return

        removed_mods = []

        for mod_name in mod_names:
            if mod_name in mods_info:
                del mods_info[mod_name]
                removed_mods.append(mod_name)

        if removed_mods:
            settings["mods_info"] = mods_info

            with settings_json.open("w", encoding="utf-8") as file:
                json.dump(
                    settings,
                    file,
                    indent=4,
                    ensure_ascii=False,
                    separators=(",", ": "),
                )

            logger.log_message(
                f"Mods successfully removed: {', '.join(removed_mods)}.",
            )
            logger.log_message(f"Settings updated in '{settings_json}'.")
        else:
            logger.log_message(
                "No mods were removed because none of the specified mods were found.",
            )

    except json.JSONDecodeError:
        logger.log_message(
            f"Error decoding JSON from file '{settings_json}'. Please check the file format.",
        )


def get_solo_cook_project_command() -> str:
    uproject_file = settings.get_uproject_file()
    if not uproject_file:
        uproject_not_found_error = (
            f'could not find the specified uproject file "{uproject_file}"'
        )
        raise FileNotFoundError(uproject_not_found_error)
    command = (
        f'"Engine\\Build\\BatchFiles\\RunUAT.{file_io.get_platform_wrapper_extension()}" {settings.get_unreal_engine_cooking_main_command()} '
        f'-project="{settings.get_uproject_file()}" '
    )
    if not unreal_engine.has_build_target_been_built(uproject_file):
        build_arg = "-build"
        command = f"{command} {build_arg}"
    for arg in settings.get_engine_cooking_args():
        command = f"{command} {arg}"
    return command


def cook(*, toggle_engine: bool) -> None:
    if toggle_engine:
        engine.toggle_engine_off()
    logger.log_message("Content Cooking Starting")
    run_proj_build_command(get_solo_cook_project_command())
    logger.log_message("Content Cook Complete")
    if toggle_engine:
        engine.toggle_engine_on()


def get_solo_package_command() -> str:
    uproject_file = settings.get_uproject_file()
    if not uproject_file:
        uproject_not_found_error = (
            f'could not find the specified uproject file "{uproject_file}"'
        )
        raise FileNotFoundError(uproject_not_found_error)
    command = (
        f'"Engine\\Build\\BatchFiles\\RunUAT.{file_io.get_platform_wrapper_extension()}" {settings.get_unreal_engine_packaging_main_command()} '
        f'-project="{settings.get_uproject_file()}"'
    )
    # technically it shouldn't auto build itself, since this is not a auto run sequence but used in an explicit command
    # if not ue_dev_py_utils.has_build_target_been_built(utilities.get_uproject_file()):
    #     command = f'{command} -build'
    for arg in settings.get_engine_packaging_args():
        command = f"{command} {arg}"
    custom_game_dir = utilities.custom_get_game_dir()
    if not custom_game_dir:
        raise NotADirectoryError('could not obtain the custom game directory')
    is_game_iostore = unreal_engine.get_is_game_iostore(
        uproject_file, custom_game_dir,
    )
    if is_game_iostore:
        command = f"{command} -iostore"
        logger.log_message("Check: Game is iostore")
    else:
        logger.log_message("Check: Game is not iostore")
    return command


def package(*, toggle_engine: bool, use_symlinks: bool) -> None:
    if toggle_engine:
        engine.toggle_engine_off()
    for entry in settings.get_mods_info_dict_from_json().keys():
        settings.settings_information.mod_names.append(entry)
    logger.log_message("Packaging Starting")
    run_proj_build_command(get_solo_package_command())
    packing.generate_mods(use_symlinks=use_symlinks)
    logger.log_message("Packaging Complete")
    if toggle_engine:
        engine.toggle_engine_on()


def resave_packages_and_fix_up_redirectors() -> None:
    unreal_engine_dir = settings.get_unreal_engine_dir()
    if not unreal_engine_dir:
        raise NotADirectoryError('was unable to locate the unreal engine directory')
    engine.close_game_engine()
    exe = unreal_engine.get_unreal_editor_exe_path(unreal_engine_dir)
    args = [
        '"{settings.get_uproject_file()}"',
        '-run=ResavePackages',
        '-fixupredirects',
    ]
    app_runner.run_app(exe_path=exe, args=args)


def cleanup_full() -> None:
    repo_path = settings.get_cleanup_repo_path()
    if not repo_path:
        raise FileNotFoundError('was unable to find the repo path for cleanup')
    logger.log_message(f'Cleaning up repo at: "{repo_path}"')
    git_path = shutil.which("git")
    if git_path is None:
        raise FileNotFoundError(
            "Git executable not found. Ensure it's installed and in your system PATH.",
        )
    git_path = Path(git_path)
    args = ["clean", "-d", "-X", "--force"]
    app_runner.run_app(
        exe_path=git_path,
        exec_mode=data_structures.ExecutionMode.ASYNC,
        args=args,
        working_dir=repo_path,
    )
    logger.log_message(f'Cleaned up repo at: "{repo_path}"')

    dist_dir = Path(f"{file_io.SCRIPT_DIR}/dist")
    if dist_dir.is_dir():
        shutil.rmtree(dist_dir)
    logger.log_message(f'Cleaned up dist dir at: "{dist_dir}"')

    temp_dir = settings.get_temp_directory()
    if temp_dir.is_dir():
        shutil.rmtree(temp_dir)
    logger.log_message(f'Cleaned up temp dir at: "{temp_dir}"')


def cleanup_cooked() -> None:
    repo_path = settings.get_cleanup_repo_path()
    if not repo_path:
        raise FileNotFoundError('was unable to find the repo path for cleanup')

    logger.log_message(
        f'Starting cleanup of Unreal Engine build directories in: "{repo_path}"',
    )

    build_dirs = ["Cooked"]

    for root, dirs, _ in repo_path.walk():
        for dir_name in dirs:
            if dir_name in build_dirs:
                full_path = Path(root / dir_name)
                shutil.rmtree(full_path)
                logger.log_message(f"Removed directory: {full_path}")


def cleanup_build() -> None:
    repo_path = settings.get_cleanup_repo_path()
    if not repo_path:
        raise FileNotFoundError('was unable to find the repo path for cleanup')

    logger.log_message(
        f'Starting cleanup of Unreal Engine build directories in: "{repo_path}"',
    )

    build_dirs = [
        "Intermediate",
        "DerivedDataCache",
        "Build",
        "Binaries",
    ]

    for root, dirs, _ in repo_path.walk():
        for dir_name in dirs:
            if dir_name in build_dirs:
                full_path = Path(root / dir_name)
                shutil.rmtree(full_path)
                logger.log_message(f"Removed directory: {full_path}")


def cleanup_game(output_json: Path | None = None) -> None:
    if output_json:
        file_list_json = output_json
    else:
        settings_json_dir = settings.settings_information.settings_json_dir.path
        if not settings_json_dir:
            raise NotADirectoryError('could not obtain your settings json directory')
        file_list_json = Path(settings_json_dir / "game_file_list.json")
    custom_game_dir = utilities.custom_get_game_dir()
    if not custom_game_dir:
        raise NotADirectoryError('could not obtain the custom game directory')
    game_directory = custom_game_dir.parent
    delete_unlisted_files(game_directory, file_list_json)


def generate_game_file_list_json(output_json: Path | None = None) -> None:
    if output_json:
        file_list_json = output_json
    else:
        settings_json_dir = settings.settings_information.settings_json_dir.path
        if not settings_json_dir:
            raise NotADirectoryError('was unable to obtain the settings json directory')
        file_list_json = Path(settings_json_dir / "game_file_list.json")
    custom_game_dir = utilities.custom_get_game_dir()
    if not custom_game_dir:
        raise NotADirectoryError('was unable to locate the game directory')
    game_directory = custom_game_dir.parent
    generate_file_paths_json(game_directory, file_list_json)


def cleanup_from_file_list(file_list_path: Path, directory: Path) -> None:
    delete_unlisted_files(directory, file_list_path)


def generate_file_list(directory: Path, file_list_path: Path) -> None:
    generate_file_paths_json(directory, file_list_path)


def generate_mods(*, input_mod_names: list[str], use_symlinks: bool) -> None:
    for mod_name in input_mod_names:
        settings.settings_information.mod_names.append(mod_name)
    packing.generate_mods(use_symlinks=use_symlinks)


def generate_mods_all(*, use_symlinks: bool) -> None:
    for mod_name in settings.get_mods_info_dict_from_json().keys():
        settings.settings_information.mod_names.append(mod_name)
        logger.log_message(mod_name)
    packing.generate_mods(use_symlinks=use_symlinks)


# doesn't account for when there are ucas/utoc to copy over
def make_unreal_pak_mod_release(
    singular_mod_info: dict, base_files_directory: Path, output_directory: Path, mod_name: str,
) -> None:
    # currently assumes mod was installed to game and not temporarily in the working dir, maybe?
    src_pak = Path(
        f"{utilities.custom_get_game_paks_dir()}/{utilities.get_pak_dir_structure(mod_name)}/{mod_name}.pak",
    )
    dest_pak_file = Path(
        f"{base_files_directory}/{mod_name}/{utilities.get_pak_dir_structure(mod_name)}/{mod_name}.pak",
    )
    if dest_pak_file.is_file():
        dest_pak_file.unlink()
    logger.log_message(dest_pak_file.parent)
    dest_pak_file.parent.mkdir(parents=True, exist_ok=True)
    if not src_pak.is_file():
        # this creates it when it doesn't exist, sometimes there are no files to make a pak, but one is needed
        src_pak.open("w").close()
    else:
        shutil.copyfile(src_pak, dest_pak_file)
    file_io.zip_directory_tree(
        input_dir=Path(f"{base_files_directory}/{mod_name}"),
        output_dir=output_directory,
        zip_name=f"{mod_name}.zip",
    )


def make_repak_mod_release(
    singular_mod_info: dict, base_files_directory: Path, output_directory: Path, mod_name: str,
) -> None:
    src_pak = Path(f"{settings.get_temp_directory()}/{utilities.get_pak_dir_structure(mod_name)}/{mod_name}.pak")
    dest_pak = Path(f"{base_files_directory}/{mod_name}/{utilities.get_pak_dir_structure(mod_name)}/{mod_name}.pak")
    if dest_pak.is_file():
        dest_pak.unlink()
    logger.log_message(dest_pak.parent)
    dest_pak.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src_pak, dest_pak)
    file_io.zip_directory_tree(
        input_dir=Path(f"{base_files_directory}/{mod_name}"),
        output_dir=output_directory,
        zip_name=f"{mod_name}.zip",
    )


def make_engine_mod_release(
    singular_mod_info: dict, base_files_directory: Path, output_directory: Path, mod_name: str,
) -> None:
    mod_files = []
    pak_chunk_num = singular_mod_info["pak_chunk_num"]
    uproject_file = settings.get_uproject_file()
    if not uproject_file:
        raise FileNotFoundError('was unable to locate the uproject file')
    custom_game_dir = utilities.custom_get_game_dir()
    if not custom_game_dir:
        raise NotADirectoryError('was unable to locate the game directory')
    uproject_dir = unreal_engine.get_uproject_dir(uproject_file)
    win_dir_str = unreal_engine.get_win_dir_str(settings.get_unreal_engine_dir())
    uproject_name = unreal_engine.get_uproject_name(uproject_file)
    prefix = f"{uproject_dir}/Saved/StagedBuilds/{win_dir_str}/{uproject_name}/Content/Paks/pakchunk{pak_chunk_num}-{win_dir_str}."
    mod_files.append(prefix)
    for file in mod_files:
        for suffix in unreal_engine.get_game_pak_folder_archives(
            uproject_file, custom_game_dir,
        ):
            dir_engine_mod = Path(f"{custom_game_dir}/Content/Paks/{utilities.get_pak_dir_structure(mod_name)}")
            dir_engine_mod.mkdir(parents=True, exist_ok=True)
            src_file = Path(f"{file}{suffix}")
            dest_file = Path(f"{base_files_directory}/{mod_name}/{utilities.get_pak_dir_structure(mod_name)}/{mod_name}.{suffix}")
            if dest_file.is_file():
                dest_file.unlink()
            dest_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src_file, dest_file)
    file_io.zip_directory_tree(
        input_dir=Path(f"{base_files_directory}/{mod_name}"),
        output_dir=output_directory,
        zip_name=f"{mod_name}.zip",
    )


def get_mod_files_asset_paths_for_loose_mods(
    mod_name: str, base_files_directory: Path,
) -> dict[Path, Path]:
    file_dict = {}
    uproject_file = settings.get_uproject_file()
    if not uproject_file:
        uproject_not_found_error = (
            f'could not find the specified uproject file "{uproject_file}"'
        )
        raise FileNotFoundError(uproject_not_found_error)
    unreal_engine_dir = settings.get_unreal_engine_dir()
    if not unreal_engine_dir:
        raise RuntimeError('Unreal engine install was not valid.')
    cooked_uproject_dir = unreal_engine.get_cooked_uproject_dir(
        uproject_file, unreal_engine_dir,
    )
    mod_info = packing.get_mod_pak_entry(mod_name)
    for asset in mod_info.get("file_includes", {}).get("asset_paths", []):
        base_path = f"{cooked_uproject_dir}/{asset}"
        for extension in file_io.get_file_extensions(base_path):
            src_file = Path(f"{base_path}.{extension}")
            dest_file = Path((f"{base_files_directory}/{mod_name}/mod_files/{asset}.{extension}"))
            file_dict[src_file] = dest_file
    return file_dict


def get_mod_files_tree_paths_for_loose_mods(
    mod_name: str, base_files_directory: Path,
) -> dict[Path, Path]:
    file_dict = {}
    uproject_file = settings.get_uproject_file()
    if not uproject_file:
        uproject_not_found_error = (
            f'could not find the specified uproject file "{uproject_file}"'
        )
        raise FileNotFoundError(uproject_not_found_error)
    unreal_engine_dir = settings.get_unreal_engine_dir()
    if not unreal_engine_dir:
        raise RuntimeError('Unreal engine install was not valid.')
    cooked_uproject_dir = unreal_engine.get_cooked_uproject_dir(
        uproject_file, unreal_engine_dir,
    )
    mod_info = packing.get_mod_pak_entry(mod_name)
    for tree in mod_info.get("file_includes", {}).get("tree_paths", []):
        tree_path = Path(f"{cooked_uproject_dir}/{tree}")
        for entry in file_io.get_files_in_tree(tree_path):
            if entry.is_file():
                base_entry = entry.with_suffix('')
                for extension in file_io.get_file_extensions(str(entry)):
                    src_path = Path(f"{base_entry}.{extension}")
                    relative_path = os.path.relpath(base_entry, cooked_uproject_dir)
                    dest_path = Path(f"{base_files_directory}/{mod_name}/mod_files/{relative_path}.{extension}")
                    file_dict[src_path] = dest_path
    return file_dict


def get_mod_files_persistent_paths_for_loose_mods(
    mod_name: str, base_files_directory: Path,
) -> dict[Path, Path]:
    file_dict = {}
    persistent_mod_dir = settings.get_persistent_mod_dir(mod_name)

    for root, _, files in persistent_mod_dir.walk():
        for file in files:
            file_path = Path(root / file)
            relative_path = os.path.relpath(file_path, persistent_mod_dir)
            after_path = Path(f"{base_files_directory}/{mod_name}/mod_files/{relative_path}")
            file_dict[file_path] = after_path
    return file_dict


def get_mod_files_mod_name_dir_paths_for_loose_mods(
    mod_name: str, base_files_directory: Path,
) -> dict[Path, Path]:
    file_dict = {}
    uproject_file = settings.get_uproject_file()
    if not uproject_file:
        uproject_not_found_error = (
            f'could not find the specified uproject file "{uproject_file}"'
        )
        raise FileNotFoundError(uproject_not_found_error)
    unreal_engine_dir = settings.get_unreal_engine_dir()
    if not unreal_engine_dir:
        raise RuntimeError('Unreal engine install was not valid.')
    mod_name_dir_name = utilities.get_mod_name_dir_name(mod_name)
    unreal_mod_tree_type_str = utilities.get_unreal_mod_tree_type_str(mod_name)
    cooked_uproject_dir = unreal_engine.get_cooked_uproject_dir(uproject_file, unreal_engine_dir)
    cooked_game_name_mod_dir = Path(f"{cooked_uproject_dir}/Content/{unreal_mod_tree_type_str}/{mod_name_dir_name}")

    for file in file_io.get_files_in_tree(cooked_game_name_mod_dir):
        relative_file_path = os.path.relpath(file, cooked_game_name_mod_dir)
        src_path = Path(file.absolute())
        dest_path = Path(f"{base_files_directory}/{mod_name}/mod_files/{relative_file_path}")
        file_dict[src_path] = dest_path
    return file_dict


def get_mod_paths_for_loose_mods(mod_name: str, base_files_directory: Path) -> dict[Path, Path]:
    file_dict = {}
    file_dict.update(
        get_mod_files_asset_paths_for_loose_mods(mod_name, base_files_directory),
    )
    file_dict.update(
        get_mod_files_tree_paths_for_loose_mods(mod_name, base_files_directory),
    )
    file_dict.update(
        get_mod_files_persistent_paths_for_loose_mods(mod_name, base_files_directory),
    )
    file_dict.update(
        get_mod_files_mod_name_dir_paths_for_loose_mods(mod_name, base_files_directory),
    )

    return file_dict


def make_loose_mod_release(
    singular_mod_info: dict, base_files_directory: Path, output_directory: Path, mod_name: str,
) -> None:
    mod_files = get_mod_paths_for_loose_mods(mod_name, base_files_directory)
    dict_keys = mod_files.keys()
    for key in dict_keys:
        src_file = key
        dest_file = mod_files[key]
        dest_file.parent.mkdir(parents=True, exist_ok=True)
        if src_file.exists():
            if dest_file.is_symlink():
                dest_file.unlink()
            if dest_file.is_file():
                dest_file.unlink()
        if src_file.is_file():
            shutil.copy(src_file, dest_file)
    file_io.zip_directory_tree(
        input_dir=Path(f"{base_files_directory}/{mod_name}"),
        output_dir=output_directory,
        zip_name=f"{mod_name}.zip",
    )

    # this doesn't use the output_dir/mod_name/mod_files convention


def make_retoc_mod_release(
    singular_mod_info: dict, base_files_directory: Path, output_directory: Path, mod_name: str,
) -> None:
    temp_dir = settings.get_temp_directory()
    pak_dir_structure = utilities.get_pak_dir_structure(mod_name)
    input_dir = Path(f"{base_files_directory}/{mod_name}")
    base_src = Path(f"{temp_dir}/{pak_dir_structure}/{mod_name}.")
    base_dest_dir = Path(f"{temp_dir}/{mod_name}/mod_files/{pak_dir_structure}")
    base_dest = Path(f"{base_dest_dir}/{mod_name}.")
    base_dest_dir.mkdir(parents=True, exist_ok=True)
    packing.install_mod_sig(mod_name=mod_name, use_symlinks=False)

    extensions = data_structures.unreal_iostore_sigs_archive_extensions

    for extension in extensions:
        src_file = Path(f"{base_src}{extension}")
        dest_file = Path(f"{base_dest}{extension}")
        if dest_file.is_file():
            dest_file.unlink()
        if src_file.is_file():
            shutil.copy(src_file, dest_file)

    file_io.zip_directory_tree(
        input_dir=input_dir,
        output_dir=output_directory,
        zip_name=f"{mod_name}.zip",
    )


def generate_mod_release(
    mod_name: str, base_files_directory: Path, output_directory: Path,
) -> None:
    singular_mod_info = settings.get_mods_info_dict_from_json()[mod_name]
    if singular_mod_info["packing_type"] == "unreal_pak":
        make_unreal_pak_mod_release(
            singular_mod_info, base_files_directory, output_directory, mod_name,
        )
    elif singular_mod_info["packing_type"] == "repak":
        make_repak_mod_release(
            singular_mod_info, base_files_directory, output_directory, mod_name,
        )
    elif singular_mod_info["packing_type"] == "engine":
        make_engine_mod_release(
            singular_mod_info, base_files_directory, output_directory, mod_name,
        )
    elif singular_mod_info["packing_type"] == "loose":
        make_loose_mod_release(
            singular_mod_info, base_files_directory, output_directory, mod_name,
        )
    elif singular_mod_info["packing_type"] == "retoc":
        make_retoc_mod_release(
            singular_mod_info, base_files_directory, output_directory, mod_name,
        )
    else:
        packing_type_error = f'The following incorrect packing type was supplied "{singular_mod_info["packing_type"]}".'
        raise ValueError(packing_type_error)


def generate_mod_releases(
    mod_names: list[str], base_files_directory: Path, output_directory: Path,
) -> None:
    for mod_name in mod_names:
        generate_mod_release(mod_name, base_files_directory, output_directory)


def generate_mod_releases_all(base_files_directory: Path, output_directory: Path) -> None:
    for mod_key in settings.get_mods_info_dict_from_json().keys():
        generate_mod_release(mod_key, base_files_directory, output_directory)


def resync_dir_with_repo() -> None:
    repo_path = settings.get_cleanup_repo_path()
    if not repo_path:
        raise FileNotFoundError('was unable to find the repo path for cleanup')
    """
    Resyncs a directory tree with its repository by discarding local changes and cleaning untracked files.

    :param repo_path: The path to the root of the git repository.
    """
    repo_path = repo_path.absolute()

    if not repo_path.is_dir():
        repo_not_exist_error = (
            f"The specified path '{repo_path}' does not exist or is not a directory."
        )
        raise FileNotFoundError(repo_not_exist_error)

    if not Path(repo_path / ".git").is_dir():
        not_valid_git_repo_path = (
            f"The specified path '{repo_path}' is not a valid Git repository."
        )
        raise ValueError(not_valid_git_repo_path)

    result = os.environ.get("git")

    if result:
        exe = Path(result)
    else:
        raise FileNotFoundError('could not locate your git install')

    args = ["clean", "-f", "-d", "-x"]
    app_runner.run_app(exe_path=exe, args=args, working_dir=repo_path)

    args = ["reset", "--hard"]
    app_runner.run_app(exe_path=exe, args=args, working_dir=repo_path)

    logger.log_message(f"Successfully resynchronized the repository at '{repo_path}'.")


def generate_uproject(
    *,
    project_file: Path,
    file_version: int = 3,
    engine_major_association: int = 4,
    engine_minor_association: int = 27,
    category: str = "Modding",
    description: str = "Uproject for modding, generated with tempo.",
    ignore_safety_checks: bool = False,
) -> str:
    project_dir = project_file.parent
    project_dir.mkdir(parents=True, exist_ok=True)

    if not ignore_safety_checks:
        # Validate file version
        if file_version not in range(1, 4):
            invalid_file_version_error = (
                f"Invalid file version: {file_version}. Valid values are 1-3."
            )
            raise ValueError(invalid_file_version_error)

        # Validate EngineMajorAssociation
        if engine_major_association not in range(4, 6):  # Only 4-5 is valid
            invalid_major_engine_version_error = f"Invalid EngineMajorAssociation: {engine_major_association}. Valid value is 4-5."
            raise ValueError(invalid_major_engine_version_error)

        # Validate EngineMinorAssociation
        if engine_minor_association not in range(28):  # Valid range is 0-27
            invalid_minor_engine_version_error = f"Invalid EngineMinorAssociation: {engine_minor_association}. Valid range is 0-27."
            raise ValueError(invalid_minor_engine_version_error)

        # Ensure the directory is empty
        project_dir = project_file.resolve().parent

        if project_dir.exists and project_dir.iterdir():
            cannot_generate_in_non_empty_dir_error = f'The directory "{project_dir}" is not empty. Cannot generate project here.'
            raise FileExistsError(cannot_generate_in_non_empty_dir_error)

    # Generate the JSON content for the .uproject file
    json_content = unreal_engine.get_new_uproject_json_contents(
        file_version,
        engine_major_association,
        engine_minor_association,
        category,
        description,
    )

    # Write the .uproject file
    try:
        with project_file.open("w") as f:
            f.write(json_content)
    except OSError as e:
        raise OSError(
            f"Failed to write to file '{project_file}': {e}",
        ) from e

    return f"Successfully generated '{project_file}'."


def add_module_to_descriptor(
    descriptor_file: Path, module_name: str, host_type: str, loading_phase: str,
) -> None:
    if not descriptor_file.is_file():
        descriptor_file_not_exist_error = (
            f"The file '{descriptor_file}' does not exist."
        )
        raise FileNotFoundError(descriptor_file_not_exist_error)

    try:
        with descriptor_file.open() as file:
            uproject_data = json.load(file)
    except json.JSONDecodeError as e:
        raise ValueError(
            f"Failed to parse JSON from '{descriptor_file}': {e}",
        ) from e

    module_entry = {
        "Name": module_name,
        "Type": host_type,
        "LoadingPhase": loading_phase,
    }

    if "Modules" not in uproject_data:
        uproject_data["Modules"] = []

    uproject_data["Modules"] = [
        module
        for module in uproject_data["Modules"]
        if module.get("Name") != module_name
    ] + [module_entry]

    updated_data = json.dumps(uproject_data, indent=4)
    try:
        with descriptor_file.open("w") as file:
            file.write(updated_data)
    except OSError as e:
        raise OSError(f"Failed to write to '{descriptor_file}': {e}") from e


def add_plugin_to_descriptor(
    descriptor_file: Path, plugin_name: str, *, is_enabled: bool,
) -> None:
    if not descriptor_file.is_file():
        file_does_not_exist_error = f"The file '{descriptor_file}' does not exist."
        raise FileNotFoundError(file_does_not_exist_error)

    try:
        with descriptor_file.open() as file:
            uproject_data = json.load(file)
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse JSON from '{descriptor_file}': {e}") from e

    plugin_entry = {"Name": plugin_name, "Enabled": is_enabled}

    if "Plugins" not in uproject_data:
        uproject_data["Plugins"] = []

    uproject_data["Plugins"] = [
        plugin
        for plugin in uproject_data["Plugins"]
        if plugin.get("Name") != plugin_name
    ] + [plugin_entry]

    updated_data = json.dumps(uproject_data, indent=4)
    try:
        with descriptor_file.open("w") as file:
            file.write(updated_data)
    except OSError as e:
        raise OSError(f"Failed to write to '{descriptor_file}': {e}") from e


def remove_modules_from_descriptor(descriptor_file: Path, module_names: list) -> None:
    if not descriptor_file.is_file():
        descriptor_not_found_error = f"The file '{descriptor_file}' does not exist."
        raise FileNotFoundError(descriptor_not_found_error)

    with descriptor_file.open() as file:
        uproject_data = json.load(file)

    if "Modules" in uproject_data:
        uproject_data["Modules"] = [
            module
            for module in uproject_data["Modules"]
            if module["Name"] not in module_names
        ]

    merged_data = json.dumps(uproject_data, indent=4)

    with descriptor_file.open("w") as file:
        file.write(merged_data)


def remove_plugins_from_descriptor(descriptor_file: Path, plugin_names: list) -> None:
    if not descriptor_file.is_file():
        descriptor_not_found_error = f"The file '{descriptor_file}' does not exist."
        raise FileNotFoundError(descriptor_not_found_error)

    with descriptor_file.open() as file:
        uproject_data = json.load(file)

    if "Plugins" in uproject_data:
        uproject_data["Plugins"] = [
            plugin
            for plugin in uproject_data["Plugins"]
            if plugin["Name"] not in plugin_names
        ]

    merged_data = json.dumps(uproject_data, indent=4)

    with descriptor_file.open("w") as file:
        file.write(merged_data)


def generate_uplugin(
    *,
    plugins_directory: Path,
    plugin_name: str,
    can_contain_content: bool,
    is_installed: bool,
    is_hidden: bool,
    no_code: bool,
    category: str,
    created_by: str,
    created_by_url: str,
    description: str,
    docs_url: str,
    editor_custom_virtual_path: str,
    enabled_by_default: bool,
    engine_major_version: int,
    engine_minor_version: int,
    support_url: str,
    version: float,
    version_name: str,
) -> None:
    plugins_directory.mkdir(parents=True, exist_ok=True)

    plugin_data = {
        "FileVersion": 3,
        "Version": version,
        "VersionName": version_name,
        "FriendlyName": plugin_name,
        "Description": description,
        "Category": category,
        "CreatedBy": created_by,
        "CreatedByURL": created_by_url,
        "DocsURL": docs_url,
        "MarketplaceURL": "",
        "SupportURL": support_url,
        "EngineVersion": f"{engine_major_version}.{engine_minor_version}",
        "EnabledByDefault": enabled_by_default,
        "CanContainContent": can_contain_content,
        "IsBetaVersion": False,
        "IsExperimentalVersion": False,
        "Installed": is_installed,
        "Hidden": is_hidden,
        "NoCode": no_code,
        "Modules": [],
        "Plugins": [],
    }

    if editor_custom_virtual_path:
        plugin_data["EditorCustomVirtualPath"] = editor_custom_virtual_path

    plugin_data_string = json.dumps(plugin_data, indent=4)

    plugin_file_path = Path(plugins_directory / plugin_name / f"{plugin_name}.uplugin")

    plugin_file_path.parent.mkdir(parents=True, exist_ok=True)

    with plugin_file_path.open("w") as plugin_file:
        plugin_file.write(plugin_data_string)

    logger.log_message(
        f"Plugin '{plugin_name}' generated successfully at {plugin_file_path}.",
    )


def remove_uplugins(uplugin_paths: list) -> None:
    for uplugin_path in uplugin_paths:
        uplugin_dir = uplugin_path.parent
        if uplugin_dir.is_dir():
            shutil.rmtree(uplugin_dir)


def generate_file_paths_json(dir_path: Path, output_json: Path) -> None:
    all_file_paths = []

    for root, _, files in dir_path.walk():
        for file in files:
            full_path = Path(root / file)
            all_file_paths.append(full_path)

    json_string = json.dumps(all_file_paths)
    output_json.parent.mkdir(parents=True, exist_ok=True)
    with output_json.open("w", encoding="utf-8") as json_file:
        json_file.write(json_string)

    logger.log_message(f"JSON file with all file paths created at: {output_json}")


def delete_unlisted_files(dir_path: Path, json_file: Path) -> None:
    with json_file.open() as file:
        allowed_files = set(json.load(file))

    for root, _, files in dir_path.walk():
        for file in files:
            full_path = Path(root / file)
            if full_path not in allowed_files:
                full_path.unlink()
                logger.log_message(f"Deleted: {full_path}")

    logger.log_message("Cleanup complete. All unlisted files have been removed.")


def save_json_to_file(json_string: str, file_path: Path) -> None:
    try:
        parsed_json = json.loads(json_string)

        with file_path.open("w") as file:
            json.dump(parsed_json, file, indent=4)

        logger.log_message(f"JSON data successfully saved to {file_path}")
    except json.JSONDecodeError as e:
        logger.log_message(f"Invalid JSON string: {e}")
