import os
import sys
import json
import enum
import shutil
import typing
import pathlib
import platform
import subprocess
from dataclasses import dataclass

from tempo_core.programs import unreal_engine
from tempo_core import file_io, logger, process_management, data_structures


class SettingsOrigin(enum.Enum):
    """
    enum for where settings came from, mostly used for relative path creation.
    From top to bottom, is the lowest to highest priority for the recieved value.
    So command_line values will be used over env_var, which will be used over env_file, and so on.
    """

    DEFAULT = "default"
    CONFIG = "config"
    ENV_FILE = "env_file"
    ENV_VAR = "env_var"
    COMMAND_LINE = "command_line"


@dataclass
class SettingSpecificInfo:
    path: pathlib.Path | None
    origin: SettingsOrigin | None


@dataclass
class SettingsInformation:
    settings: dict[str, typing.Any]
    init_settings_done: bool
    settings_json_dir: SettingSpecificInfo
    program_dir: SettingSpecificInfo
    mod_names: list[str]
    settings_json: SettingSpecificInfo


settings_information = SettingsInformation(
    settings={},
    init_settings_done=False,
    settings_json_dir=SettingSpecificInfo(None, None),
    program_dir=SettingSpecificInfo(None, None),
    mod_names=[],
    settings_json=SettingSpecificInfo(None, None),
)


def init_settings(settings_json_path: pathlib.Path):
    with open(settings_json_path, "r") as file:
        raw_settings = json.load(file)
    # raw_settings = Dynaconf(settings_files=[settings_json_path])
    # settings_information.settings = configs.DynamicSettings(raw_settings)
    settings_information.settings = raw_settings
    settings = settings_information.settings
    process_name = os.path.basename(
        settings.get("game_info", {}).get("game_exe_path", "")
    )
    # window_management.change_window_name(settings["general_info"]["window_title"])
    auto_close_game = settings.get("process_kill_events", {}).get(
        "auto_close_game", True
    )
    is_process_running = process_management.is_process_running(process_name)
    if auto_close_game and is_process_running:
        current_os = platform.system()

        if current_os == "Windows":
            taskkill_path = shutil.which("taskkill")

            if taskkill_path:
                if process_name != "":
                    subprocess.run(
                        [taskkill_path, "/F", "/IM", process_name], check=False
                    )
            else:
                raise FileNotFoundError("taskkill.exe not found.")

        elif current_os == "Linux":
            # Try to use `pkill` or `killall` if available
            pkill_path = shutil.which("pkill")
            killall_path = shutil.which("killall")

            if process_name != "":
                if pkill_path:
                    subprocess.run([pkill_path, "-f", process_name], check=False)
                elif killall_path:
                    subprocess.run([killall_path, process_name], check=False)
                else:
                    raise FileNotFoundError("Neither pkill nor killall found.")
        else:
            raise NotImplementedError(f"Unsupported OS: {current_os}")
    settings_information.init_settings_done = True
    print(f'settings_json_path: {settings_json_path}')
    settings_information.settings_json = SettingSpecificInfo(path=pathlib.Path(settings_json_path), origin=SettingsOrigin.COMMAND_LINE)
    settings_information.settings_json_dir = SettingSpecificInfo(path=pathlib.Path(settings_json_path).parent, origin=SettingsOrigin.COMMAND_LINE)


def load_settings(settings_json: str):
    logger.log_message(f"settings json: {settings_json}")
    if not settings_information.init_settings_done:
        init_settings(pathlib.Path(settings_json))


def get_unreal_engine_dir() -> pathlib.Path | None:
    unreal_engine_directory = settings_information.settings.get("engine_info", {}).get("unreal_engine_dir", None)
    if unreal_engine_directory and not os.path.isabs(unreal_engine_directory):
        unreal_engine_directory = pathlib.Path(str(settings_information.settings_json_dir.path), unreal_engine_directory)
    else:
        unreal_version = get_unreal_engine_version(engine_path=None)
        env_var_string_one = 'UNREAL_ENGINE_DIRECTORY'
        env_var_string_two = f'TEMPO_{env_var_string_one}'
        env_var_string_three = f'{env_var_string_one}_{unreal_version.major_version}_{unreal_version.minor_version}'
        env_var_string_four = f'TEMPO_{env_var_string_three}'
        var_one = os.environ.get(env_var_string_one)
        var_two = os.environ.get(env_var_string_two)
        var_three = os.environ.get(env_var_string_three)
        var_four = os.environ.get(env_var_string_four)
        # print(env_var_string_one)
        # print(env_var_string_two)
        # print(env_var_string_three)
        # print(env_var_string_four)
        # print(f'var one: {var_one}')
        # print(f'var two: {var_two}')
        # print(f'var three: {var_three}')
        # print(f'var four: {var_four}')
        unreal_engine_directory = var_four or var_three or var_two or var_one
    file_io.check_path_exists(str(unreal_engine_directory))
    return unreal_engine_directory


def is_unreal_pak_packing_enum_in_use() -> bool:
    is_in_use = False
    for entry in get_mods_info_list_from_json():
        if entry["packing_type"] == "unreal_pak":
            is_in_use = True
    return is_in_use


def is_engine_packing_enum_in_use() -> bool:
    is_in_use = False
    for entry in get_mods_info_list_from_json():
        if entry["packing_type"] == "engine":
            is_in_use = True
    return is_in_use


def is_repak_packing_enum_in_use() -> bool:
    is_in_use = False
    for entry in get_mods_info_list_from_json():
        if entry["packing_type"] == "repak":
            is_in_use = True
    return is_in_use


def is_retoc_packing_enum_in_use() -> bool:
    is_in_use = False
    for entry in get_mods_info_list_from_json():
        if entry["packing_type"] == "retoc":
            is_in_use = True
    return is_in_use


def is_loose_packing_enum_in_use() -> bool:
    is_in_use = False
    for entry in get_mods_info_list_from_json():
        if entry["packing_type"] == "loose":
            is_in_use = True
    return is_in_use


def get_game_exe_path() -> pathlib.Path | None:
    game_exe_path = settings_information.settings.get("game_info", {}).get("game_exe_path", None)
    if game_exe_path and not os.path.isabs(game_exe_path):
        game_exe_path = pathlib.Path(str(settings_information.settings_json_dir.path), game_exe_path)
    if game_exe_path:
        return game_exe_path
    return None


def get_git_info_repo_path() -> pathlib.Path | None:
    raw_path = settings_information.settings.get("git_info", {}).get(
        "repo_path", None
    )
    if not raw_path:
        return None

    if not os.path.isabs(raw_path):
        return pathlib.Path(str(settings_information.settings_json_dir.path), raw_path).resolve()
    else:
        return pathlib.Path(raw_path).resolve()



def get_game_launcher_exe_path() -> pathlib.Path | None:
        game_launcher_exe_path = settings_information.settings.get("game_info", {}).get("game_launcher_exe", None)
        if game_launcher_exe_path and not os.path.isabs(game_launcher_exe_path):
            game_launcher_exe_path = pathlib.Path(str(settings_information.settings_json_dir.path), game_launcher_exe_path)
        if game_launcher_exe_path:
            return game_launcher_exe_path
        return None


def get_uproject_file() -> pathlib.Path | None:
    raw_path = settings_information.settings.get("engine_info", {}).get(
        "unreal_project_file", None
    )
    settings_dir = str(settings_information.settings_json_dir.path)
    if not raw_path or not os.path.isdir(settings_dir):
        return None

    if not os.path.isabs(raw_path):
        return pathlib.Path(settings_dir, raw_path).resolve()
        # raw_path = os.path.join(file_io.SCRIPT_DIR, raw_path)
        # raw_path = os.path.join(get_temp_directory(), raw_path)
        # raw_path = os.path.join(settings_dir, raw_path
    else:
        return pathlib.Path(raw_path).resolve()


# import traceback
# def get_uproject_file() -> pathlib.Path | None:
#     raw_path = settings_information.settings.get("engine_info", {}).get(
#         "unreal_project_file", None
#     )
#     settings_dir = str(settings_information.settings_json_dir.path)

#     # --- Debug output ---
#     print("\n[get_uproject_file_debug] Called")
#     print(f"  raw_path: {raw_path!r}")
#     print(f"  settings_dir: {settings_dir!r}")
#     print(f"  settings_dir exists: {os.path.isdir(settings_dir)}")
#     print(f"  is raw_path absolute: {os.path.isabs(raw_path) if raw_path else None}")

#     # Optional: print the callsite
#     print("  Call stack:")
#     for line in traceback.format_stack(limit=5):
#         print("    " + line.strip())

#     if not raw_path:
#         print("  -> returning None (raw_path is empty)")
#         return None

#     if not os.path.isdir(settings_dir):
#         print("  -> returning None (settings_dir does not exist)")
#         return None

#     # Build final path
#     if not os.path.isabs(raw_path):
#         final = pathlib.Path(settings_dir, raw_path).resolve()
#         print(f"  -> relative path resolved to: {str(final)!r}")
#         return final
#     else:
#         final = pathlib.Path(raw_path).resolve()
#         print(f"  -> absolute path resolved to: {str(final)!r}")
#         return final


# def get_uproject_file() -> pathlib.Path | None:
#     raw_path = settings_information.settings.get("engine_info", {}).get(
#         "unreal_project_file", None
#     )
#     settings_dir = str(settings_information.settings_json_dir.path)
#     if not raw_path or not os.path.isdir(settings_dir):
#         return None

#     if not os.path.isabs(raw_path):
#         return pathlib.Path(settings_dir, raw_path).resolve()
#         # raw_path = os.path.join(file_io.SCRIPT_DIR, raw_path)
#         # raw_path = os.path.join(get_temp_directory(), raw_path)
#         # raw_path = os.path.join(settings_dir, raw_path
#     else:
#         return pathlib.Path(raw_path).resolve()


def get_uproject_name() -> str | None:
    uproject_file = get_uproject_file()
    if not uproject_file:
        return None
    return os.path.splitext(os.path.basename(uproject_file))[0]


def get_unreal_engine_packaging_main_command() -> str:
    return settings_information.settings.get("engine_info", {}).get(
        "engine_packaging_command", "BuildCookRun"
    )


def get_unreal_engine_cooking_main_command() -> str:
    return settings_information.settings.get("engine_info", {}).get(
        "engine_cooking_command", "BuildCookRun"
    )


def get_unreal_engine_building_main_command() -> str:
    return settings_information.settings.get("engine_info", {}).get(
        "engine_building_command", "BuildCookRun"
    )


def get_cleanup_repo_path() -> pathlib.Path | None:
    raw_path = settings_information.settings.get("git_info", {}).get(
        "repo_path", None
    )
    if not raw_path:
        return None

    if not os.path.isabs(raw_path):
        return pathlib.Path(str(settings_information.settings_json_dir.path), raw_path).resolve()
    else:
        return pathlib.Path(raw_path).resolve()


def get_window_title_override() -> str | None:
    return settings_information.settings.get("game_info", {}).get(
        "window_title_override", None
    )


def get_engine_building_args() -> list:
    default_args = ["-build", "-skipstage", "-nodebuginfo", "-noP4"]
    return settings_information.settings.get("engine_info", {}).get(
        "engine_building_args", default_args
    )


def get_engine_packaging_args() -> list:
    default_args = [
        "-stage",
        "-pak",
        "-cook",
        "-unversionedcookedcontent",
        "-SkipCookingEditorContent",
        "-iterate",
        "-noP4",
        "-compressed",
    ]
    return settings_information.settings.get("engine_info", {}).get(
        "engine_packaging_args", default_args
    )


def get_engine_cooking_args() -> list:
    default_args = [
        "-cook",
        "-unversionedcookedcontent",
        "-SkipCookingEditorContent",
        "-iterate",
        "-noP4",
    ]
    return settings_information.settings.get("engine_info", {}).get(
        "engine_cooking_args", default_args
    )


def get_window_management_events() -> dict:
    return settings_information.settings.get("window_management_events", [])


def get_persistent_mod_dir(mod_name: str) -> str:
    return os.path.normpath(
        f"{settings_information.settings_json_dir}/mod_packaging/persistent_files/{mod_name}"
    )


def get_persistent_mods_dir() -> str:
    return os.path.normpath(
        f"{settings_information.settings_json_dir}/mod_packaging/persistent_files"
    )


def get_alt_packing_dir_name() -> str | None:
    return settings_information.settings.get("packaging_uproject_name", {}).get(
        "name", None
    )


def get_mods_info_list_from_json() -> list:
    return settings_information.settings.get("mods_info", [])


def get_exec_events() -> list:
    return settings_information.settings.get("exec_events", [])


def get_ide_path() -> pathlib.Path | None:
    raw_path = settings_information.settings.get("optionals", {}).get(
        "ide_path", None
    )
    if not raw_path:
        return None

    if not os.path.isabs(raw_path):
        return pathlib.Path(str(settings_information.settings_json_dir.path), raw_path).resolve()
    else:
        return pathlib.Path(raw_path).resolve()


def get_blender_path() -> pathlib.Path | None:
    raw_path = settings_information.settings.get("optionals", {}).get(
        "blender_path", None
    )
    if not raw_path:
        return None

    if not os.path.isabs(raw_path):
        return pathlib.Path(str(settings_information.settings_json_dir.path), raw_path).resolve()
    else:
        return pathlib.Path(raw_path).resolve()


def get_game_info_launch_type_enum_str_value() -> str:
    return settings_information.settings["game_info"]["launch_type"]


def get_game_id() -> int:
    return settings_information.settings["game_info"]["game_id"]


def get_game_launch_params() -> list:
    return settings_information.settings.get("game_info", {}).get("launch_params", [])


def get_engine_launch_args() -> list:
    return settings_information.settings.get("engine_info", {}).get(
        "engine_launch_args", []
    )


# priority is not proper now for this I think
def get_unreal_engine_version(engine_path: str | None) -> data_structures.UnrealEngineVersion:
    potential_valid_minor_version = settings_information.settings.get(
        "engine_info", {}
    ).get("unreal_engine_minor_version", None)
    potential_valid_major_version = settings_information.settings.get(
        "engine_info", {}
    ).get("unreal_engine_major_version", None)
    if not engine_path:
        var_one = 'TEMPO_UNREAL_ENGINE_MAJOR_VERSION'
        var_two = 'TEMPO_UNREAL_ENGINE_MINOR_VERSION'
        var_three = 'UNREAL_ENGINE_MAJOR_VERSION'
        var_four = 'UNREAL_ENGINE_MINOR_VERSION'
        var_five = os.environ.get(var_one)
        var_six = os.environ.get(var_two)
        var_seven = os.environ.get(var_three)
        var_eight = os.environ.get(var_four)
        prioritized_major_value = var_five or var_eight
        prioritized_minor_value = var_six or var_seven
        if prioritized_major_value and prioritized_minor_value:
            return data_structures.UnrealEngineVersion(major_version=int(prioritized_major_value), minor_version=int(prioritized_minor_value))
        else:
            raise RuntimeError('There was no valid unreal engine version findeable from env var, env file, config, param, or auto detected through game install, or unreal engine build version. Please specify somehow.')
    elif potential_valid_minor_version and potential_valid_major_version:
        unreal_engine_version = data_structures.UnrealEngineVersion(
            minor_version=int(potential_valid_minor_version),
            major_version=int(potential_valid_major_version),
        )
    else:
        unreal_engine_version = (
            unreal_engine.get_unreal_engine_version_from_build_version_file(engine_path)
        )
    # add other ways to grab this later, like patternsleuth through game scan
    return unreal_engine_version


def get_temp_directory() -> str:
    temp_dir = os.path.join(file_io.SCRIPT_DIR, "temp")
    os.makedirs(temp_dir, exist_ok=True)
    return os.path.normpath(temp_dir)


# want to use this instead, but it tends to give permission errors
# def get_temp_directory() -> str:
#     return os.path.normpath(tempfile.gettempdir())


def should_show_progress_bars() -> bool:
    return "--disable_progress_bars" not in sys.argv


def is_windows():
    return platform.system() == "Windows"


def is_linux():
    return platform.system() == "Linux"


def get_is_game_iostore_from_config() -> bool | None:
    # Have this check manually passed param, env file, env var, config param, check from game, default to none
    return settings_information.settings.get("game_info", {}).get("is_iostore", None)
