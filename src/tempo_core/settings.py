import os
import sys
import pathlib
import shutil
import subprocess
from dataclasses import dataclass
from typing import Any
import json
import platform

from tempo_core import (
    file_io,
    logger,
    process_management,
    data_structures
)
from tempo_core.programs import unreal_engine


@dataclass
class SettingsInformation:
    settings: dict[str, Any]
    init_settings_done: bool
    settings_json_dir: str
    program_dir: str
    mod_names: list[str]
    settings_json: str


settings_information = SettingsInformation(
    settings={},
    init_settings_done=False,
    settings_json_dir="",
    program_dir="",
    mod_names=[],
    settings_json="",
)


def init_settings(settings_json_path: pathlib.Path):
    with open(settings_json_path, "r") as file:
        raw_settings = json.load(file)
    # raw_settings = Dynaconf(settings_files=[settings_json_path])
    # settings_information.settings = configs.DynamicSettings(raw_settings)
    settings_information.settings = raw_settings
    settings = settings_information.settings
    process_name = os.path.basename(settings.get("game_info", {}).get("game_exe_path", ''))
    # window_management.change_window_name(settings["general_info"]["window_title"])
    auto_close_game = settings["process_kill_events"]["auto_close_game"]
    is_process_running = process_management.is_process_running(process_name)
    if auto_close_game and is_process_running:
        current_os = platform.system()

        if current_os == "Windows":
            taskkill_path = shutil.which("taskkill")

            if taskkill_path:
                if process_name != '':
                    subprocess.run([taskkill_path, "/F", "/IM", process_name], check=False)
            else:
                raise FileNotFoundError("taskkill.exe not found.")
        
        elif current_os == "Linux":
            # Try to use `pkill` or `killall` if available
            pkill_path = shutil.which("pkill")
            killall_path = shutil.which("killall")

            if process_name != '':
                if pkill_path:
                    subprocess.run([pkill_path, "-f", process_name], check=False)
                elif killall_path:
                    subprocess.run([killall_path, process_name], check=False)
                else:
                    raise FileNotFoundError("Neither pkill nor killall found.")
        else:
            raise NotImplementedError(f"Unsupported OS: {current_os}")
    settings_information.init_settings_done = True
    settings_information.settings_json = str(settings_json_path)
    settings_information.settings_json_dir = os.path.dirname(
        settings_information.settings_json
    )


def load_settings(settings_json: str):
    logger.log_message(f"settings json: {settings_json}")
    if not settings_information.init_settings_done:
        init_settings(pathlib.Path(settings_json))


def get_unreal_engine_dir() -> str:
    ue_dir = settings_information.settings["engine_info"]["unreal_engine_dir"]
    file_io.check_path_exists(ue_dir)
    return ue_dir


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


def get_game_exe_path() -> str | None:
    return settings_information.settings.get("game_info", {}).get("game_exe_path", None)


def get_git_info_repo_path() -> str:
    return settings_information.settings["git_info"]["repo_path"]


def get_game_launcher_exe_path() -> str | None:
    return settings_information.settings.get('game_info', {}).get('game_launcher_exe', None)


def get_uproject_file() -> str:
    return settings_information.settings["engine_info"]["unreal_project_file"]


def get_unreal_engine_packaging_main_command() -> str:
    return settings_information.settings.get("engine_info", {}).get("engine_packaging_command", "BuildCookRun")


def get_unreal_engine_cooking_main_command() -> str:
    return settings_information.settings.get("engine_info", {}).get("engine_cooking_command", "BuildCookRun")


def get_unreal_engine_building_main_command() -> str:
    return settings_information.settings.get("engine_info", {}).get("engine_building_command", "BuildCookRun")


def get_cleanup_repo_path() -> str:
    return settings_information.settings["git_info"]["repo_path"]


def get_window_title_override() -> str | None:
    return settings_information.settings.get('game_info', {}).get('window_title_override', None)


def get_engine_building_args() -> list:
    default_args = [
      "-build",
      "-skipstage",
      "-nodebuginfo",
      "-noP4"
    ]
    return settings_information.settings.get("engine_info", {}).get("engine_building_args", default_args)


def get_engine_packaging_args() -> list:
    default_args = [
      "-stage",
      "-pak",
      "-cook",
      "-unversionedcookedcontent",
      "-SkipCookingEditorContent",
      "-iterate",
      "-noP4",
      "-compressed"
    ]
    return settings_information.settings.get("engine_info", {}).get("engine_packaging_args", default_args)


def get_engine_cooking_args() -> list:
    default_args = [
      "-cook",
      "-unversionedcookedcontent",
      "-SkipCookingEditorContent",
      "-iterate",
      "-noP4"
    ]
    return settings_information.settings.get("engine_info", {}).get("engine_cooking_args", default_args)


def get_window_management_events() -> dict:
    return settings_information.settings.get("window_management_events", [])


def get_persistent_mod_dir(mod_name: str) -> str:
    return os.path.normpath(f"{settings_information.settings_json_dir}/mod_packaging/persistent_files/{mod_name}")


def get_persistent_mods_dir() -> str:
    return os.path.normpath(f"{settings_information.settings_json_dir}/mod_packaging/persistent_files")


def get_alt_packing_dir_name() -> str | None:
    return settings_information.settings.get('packaging_uproject_name', {}).get('name', None)


def get_mods_info_list_from_json() -> list:
    return settings_information.settings.get("mods_info", [])


def get_exec_events() -> list:
    return settings_information.settings.get("exec_events", [])


def get_ide_path() -> str:
    return settings_information.settings["optionals"]["ide_path"]


def get_blender_path():
    return settings_information.settings["optionals"]["blender_path"]


def get_game_info_launch_type_enum_str_value() -> str:
    return settings_information.settings["game_info"]["launch_type"]


def get_game_id() -> int:
    return settings_information.settings["game_info"]["game_id"]


def get_game_launch_params() -> list:
    return settings_information.settings.get("game_info", {}).get("launch_params", [])


def get_engine_launch_args() -> list:
    return settings_information.settings.get("engine_info", {}).get("engine_launch_args", [])


def get_unreal_engine_version(engine_path: str) -> data_structures.UnrealEngineVersion:
    potential_valid_minor_version = settings_information.settings.get('engine_info', {}).get('unreal_engine_minor_version', None)
    potential_valid_major_version = settings_information.settings.get('engine_info', {}).get('unreal_engine_major_version', None)
    if potential_valid_minor_version and potential_valid_major_version:
        unreal_engine_version = data_structures.UnrealEngineVersion(
            minor_version=int(potential_valid_minor_version), 
            major_version=int(potential_valid_major_version )
        )
    else:
        unreal_engine_version = unreal_engine.get_unreal_engine_version_from_build_version_file(engine_path)
    # add other ways to grab this later, like patternsleuth through game scan
    return unreal_engine_version


def get_working_dir() -> str:
    working_dir = os.path.join(file_io.SCRIPT_DIR, "working_dir")
    os.makedirs(working_dir, exist_ok=True)
    return working_dir


def should_show_progress_bars() -> bool:
    return "--disable_progress_bars" not in sys.argv


def is_windows():
    return platform.system() == "Windows"


def is_linux():
    return platform.system() == "Linux"
