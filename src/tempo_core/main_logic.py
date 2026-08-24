import json
import shutil
import subprocess
from pathlib import Path
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
    manager,
    checks,
    timer
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


def build(*, toggle_engine: bool) -> None:
    if toggle_engine:
        engine.toggle_engine_off()
    packing.build_uproject()
    if toggle_engine:
        engine.toggle_engine_on()


def cook(*, toggle_engine: bool) -> None:
    if toggle_engine:
        engine.toggle_engine_off()
    logger.log_message("Content Cooking Starting")
    packing.cook_uproject()
    logger.log_message("Content Cook Complete")
    if toggle_engine:
        engine.toggle_engine_on()


def package(*, toggle_engine: bool, use_symlinks: bool) -> None:
    if toggle_engine:
        engine.toggle_engine_off()
    settings.settings_information.mod_names.update(settings.get_mods_info_dict_from_json().keys())
    checks.atleast_one_enabled_mod_check()
    logger.log_message("Packaging Starting")
    packing.run_proj_command(packing.get_solo_package_command())
    packing.generate_mods(use_symlinks=use_symlinks)
    logger.log_message("Packaging Complete")
    if toggle_engine:
        engine.toggle_engine_on()


def test_mods(*, input_mod_names: list[str], toggle_engine: bool, use_symlinks: bool) -> None:
    if toggle_engine:
        engine.toggle_engine_off()
    settings.settings_information.mod_names.update(input_mod_names)
    checks.atleast_one_enabled_mod_check()
    packing.build_cook()
    packing.generate_mods(use_symlinks=use_symlinks)
    game_runner.run_game()
    game_monitor.game_monitor_thread()
    if toggle_engine:
        engine.toggle_engine_on()


def test_mods_all(*, toggle_engine: bool, use_symlinks: bool) -> None:
    if toggle_engine:
        engine.toggle_engine_off()
    mod_info_dict = settings.settings_information.settings.get("mods_info", {})
    settings.settings_information.mod_names.update(mod_info_dict.keys())
    checks.atleast_one_enabled_mod_check()
    packing.build_cook()
    packing.generate_mods(use_symlinks=use_symlinks)
    game_runner.run_game()
    game_monitor.game_monitor_thread()
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
    settings.settings_information.mod_names.update(input_mod_names)
    checks.atleast_one_enabled_mod_check()
    packing.build_cook()
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
    settings.settings_information.mod_names.update(settings.get_mods_info_dict_from_json().keys())
    checks.atleast_one_enabled_mod_check()
    packing.build_cook()
    generate_mods_all(use_symlinks=use_symlinks)
    generate_mod_releases_all(
        base_files_directory=base_files_directory, output_directory=output_directory,
    )
    if toggle_engine:
        engine.toggle_engine_on()

        
def generate_mods(*, input_mod_names: list[str], use_symlinks: bool) -> None:
    settings.settings_information.mod_names.update(input_mod_names)
    checks.atleast_one_enabled_mod_check()
    packing.generate_mods(use_symlinks=use_symlinks)


def generate_mods_all(*, use_symlinks: bool) -> None:
    settings.settings_information.mod_names.update(settings.get_mods_info_dict_from_json().keys())
    checks.atleast_one_enabled_mod_check()
    packing.generate_mods(use_symlinks=use_symlinks)


def generate_mod_releases(
    mod_names: list[str], base_files_directory: Path, output_directory: Path,
) -> None:
    settings.settings_information.mod_names.update(mod_names)
    checks.atleast_one_enabled_mod_check()
    for mod_name in settings.get_enabled_mod_names():
        packing.generate_mod_release(mod_name, base_files_directory, output_directory)


def generate_mod_releases_all(base_files_directory: Path, output_directory: Path) -> None:
    mod_info_dict = settings.settings_information.settings.get("mods_info", {})
    settings.settings_information.mod_names.update(mod_info_dict.keys())
    checks.atleast_one_enabled_mod_check()
    for mod_name in settings.get_enabled_mod_names():
        packing.generate_mod_release(mod_name, base_files_directory, output_directory)
    logger.log_message(
        f"Timer: Time since script execution: {timer.get_running_time()}",
    )












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


def enable_mods(config_file: Path, mod_names: list) -> None:
    try:
        with config_file.open(encoding="utf-8") as file:
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

            with config_file.open("w", encoding="utf-8") as file:
                file.write(updated_json_str)

            logger.log_message(f"Mods successfully enabled in '{config_file}'.")
        else:
            logger.log_message(
                "No mods were enabled because all specified mods were already enabled.",
            )

    except json.JSONDecodeError:
        logger.log_message(
            f"Error decoding JSON from file '{config_file}'. Please check the file format.",
        )


def disable_mods(config_file: Path, mod_names: list) -> None:
    try:
        with config_file.open(encoding="utf-8") as file:
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

            with config_file.open("w", encoding="utf-8") as file:
                file.write(updated_json_str)

            logger.log_message(f"Mods successfully disabled in '{config_file}'.")
        else:
            logger.log_message(
                "No mods were disabled because all specified mods were already disabled.",
            )

    except json.JSONDecodeError:
        logger.log_message(
            f"Error decoding JSON from file '{config_file}'. Please check the file format.",
        )


def add_mod(
    *,
    config_file: Path,
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
        with config_file.open() as file:
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

        with config_file.open("w") as file:
            json.dump(settings, file, indent=4)

        logger.log_message(
            f"Mod '{mod_name}' successfully added/updated in '{config_file}'.",
        )

    except json.JSONDecodeError:
        logger.log_message(
            f"Error decoding JSON from file '{config_file}'. Please check the file format.",
        )


def remove_mods(config_file: Path, mod_names: list) -> None:
    try:
        with config_file.open(encoding="utf-8") as file:
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

            with config_file.open("w", encoding="utf-8") as file:
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
            logger.log_message(f"Settings updated in '{config_file}'.")
        else:
            logger.log_message(
                "No mods were removed because none of the specified mods were found.",
            )

    except json.JSONDecodeError:
        logger.log_message(
            f"Error decoding JSON from file '{config_file}'. Please check the file format.",
        )


def resave_packages_and_fix_up_redirectors() -> None:
    unreal_engine_dir = settings.get_unreal_engine_dir_or_raise()
    engine.close_game_engine()
    exe = unreal_engine.get_unreal_editor_exe_path(unreal_engine_dir)
    args = [
        f'"{settings.get_uproject_file_or_raise()}"',
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
        exec_mode=data_structures.ExecutionMode.SYNC,
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
        config_file_dir = settings.settings_information.config_file_dir.path
        if not config_file_dir:
            raise NotADirectoryError('could not obtain your settings json directory')
        file_list_json = Path(config_file_dir / "game_file_list.json")
    custom_game_dir = utilities.get_game_dir_or_raise()
    game_directory = custom_game_dir.parent
    file_io.delete_unlisted_files(game_directory, file_list_json)


def generate_game_file_list_json(output_json: Path | None = None) -> None:
    if output_json:
        file_list_json = output_json
    else:
        config_file_dir = settings.settings_information.config_file_dir.path
        if not config_file_dir:
            raise NotADirectoryError('was unable to obtain the settings json directory')
        file_list_json = Path(config_file_dir / "game_file_list.json")
    custom_game_dir = utilities.get_game_dir_or_raise()
    game_directory = custom_game_dir.parent
    file_io.generate_file_paths_json(game_directory, file_list_json)


def cleanup_from_file_list(file_list_path: Path, directory: Path) -> None:
    file_io.delete_unlisted_files(directory, file_list_path)


def generate_file_list(directory: Path, file_list_path: Path) -> None:
    file_io.generate_file_paths_json(directory, file_list_path)


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

    # result = os.environ.get("git")
    result = shutil.which("git")

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

        if project_dir.exists and sum(1 for p in project_dir.rglob("*") if p.is_file()) > 0:
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

    if can_contain_content:
        content_path = Path(plugins_directory / plugin_name / 'Content')
        content_path.mkdir(exist_ok=True)

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
