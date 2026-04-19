import os
import pathlib
import sys
import shutil

from tempo_core import (
    customization,
    file_io,
    logger,
    main_logic,
    settings,
    wrapper
)
from tempo_core.programs import unreal_engine
from tempo_core import online_check
# from tempo_core.threads import input_monitor

from tempo_cache import cache


ORIGINAL_CWD = os.getcwd()


def get_editor_preferences_ini_path() -> pathlib.Path | None:
    unreal_engine_dir = settings.get_unreal_engine_dir()
    if unreal_engine_dir:
        unreal_version = settings.get_unreal_engine_version(str(unreal_engine_dir))
    else:
        unreal_version = settings.get_unreal_engine_version(str(None))
    win_dir_str = 'Windows'
    if unreal_version:
        if unreal_version.major_version == 5:
            win_dir_str = f'{win_dir_str}Editor'
        uproject_dir = os.path.dirname(str(settings.get_uproject_file()))
        return pathlib.Path(f'{uproject_dir}/Saved/Config/{win_dir_str}/EditorPerProjectUserSettings.ini')
    return None


def is_assign_chunk_id_warning_being_suppressed() -> bool:
    def env_var_is_true(name: str) -> bool:
        value = os.getenv(name)
        if value is None:
            return False
        return value.strip().lower() in {"1", "true", "yes", "on"}

    if env_var_is_true("TEMPO_SUPPRESS_ASSIGN_CHUNK_ID_WARNING"):
        return True

    if env_var_is_true("SUPPRESS_ASSIGN_CHUNK_ID_WARNING"):
        return True

    return False


def get_compare_string() -> str:
    return "bContextMenuChunkAssignments=True"


def throw_avoid_assign_chunk_id_usage_warning() -> None:
    warning_message = f"""
Warning: The use of manually assigning chunk ids through the right click context menu of unreal is often bugged.
It will result in unexpected packaging issues.
It is reccomended to disable this setting, and do a fresh project clean before starting more work.
You can disable this through the editor preferences in unreal, or manually.
To manually disable chunk ids open "{get_editor_preferences_ini_path()}" and change {get_compare_string()} to False.
To clean your project, close unreal editor and run the tempo_cli cleanup_full command, or you can manually delete
the following directories within your unreal uproject directory.
Saved, Cooked, Intermediate, DerivedDataCache, Build, and Binaries.
If you would like to suppress this warning, you can set the TEMPO_SUPPRESS_ASSIGN_CHUNK_ID_WARNING env var to True
You can also set SUPPRESS_ASSIGN_CHUNK_ID_WARNING env var to True as well, but this will be checked secondarily.
    """
    logger.log_message(warning_message)


def assign_chunk_id_usage_check() -> None:
    ini_path = get_editor_preferences_ini_path()
    if ini_path:
        if ini_path.exists():
            lines = file_io.get_all_lines_in_config(str(ini_path))
            for line in lines:
                if get_compare_string() == line.strip():
                    throw_avoid_assign_chunk_id_usage_warning()


def uproject_check() -> None:
    uproject_file = settings.get_uproject_file()

    if not uproject_file:
        logger.log_message("Error: No uproject file path provided.")
        return

    # Try full path first
    if os.path.isfile(uproject_file):
        logger.log_message("Check: Uproject file exists at provided path.")
        return

    # Try relative to current working directory
    relative_path = os.path.join(os.getcwd(), uproject_file)
    if os.path.isfile(relative_path):
        logger.log_message("Check: Uproject file exists at relative path.")
        return

    logger.log_message(
        f"Error: Uproject file not found at '{uproject_file}' or '{relative_path}'."
    )


def unreal_engine_check() -> None:
    should_do_check = True

    if (
        not settings.is_unreal_pak_packing_enum_in_use()
        or settings.is_engine_packing_enum_in_use()
    ):
        should_do_check = False

    if should_do_check:
        engine_str = "UE4Editor"
        if unreal_engine.is_game_ue5(str(settings.get_unreal_engine_dir())):
            engine_str = "UnrealEditor"
        file_io.verify_file_exists(
            f"{settings.get_unreal_engine_dir()}/Engine/Binaries/Win64/{engine_str}.exe"
        )
        logger.log_message("Check: Unreal Engine exists")


def game_launcher_exe_override_check() -> None:
    potential_game_launcher_path = settings.get_game_launcher_exe_path()
    if potential_game_launcher_path:
        file_io.verify_file_exists(str(potential_game_launcher_path))


def git_info_check() -> None:
    git_repo_path = settings.get_git_info_repo_path()
    if git_repo_path is None or git_repo_path == "":
        return

    file_io.verify_directory_exists(str(git_repo_path))


def game_exe_check() -> None:
    file_io.verify_file_exists(str(settings.get_game_exe_path()))


def clear_temp_dir() -> None:
    temp_dir = settings.get_temp_directory()
    if os.path.isdir(temp_dir):
        shutil.rmtree(temp_dir)


def initialization() -> None:
    # input_monitor.InputMonitor().start()

    if "--logs_directory" in sys.argv:
        index = sys.argv.index("--logs_directory") + 1
        if index < len(sys.argv):
            log_dir = f"{os.path.normpath(sys.argv[index].strip("'").strip('"'))}"
            logger.set_log_base_dir(log_dir)
            logger.configure_logging()
        else:
            logger.set_log_base_dir(os.path.normpath(f"{file_io.SCRIPT_DIR}/logs"))
            logger.configure_logging()
    else:
        logger.set_log_base_dir(os.path.normpath(f"{file_io.SCRIPT_DIR}/logs"))
        logger.configure_logging()
    if "--log_name_prefix" in sys.argv:
        index = sys.argv.index("--log_name_prefix") + 1
        if index < len(sys.argv):
            logger.log_information.log_prefix = sys.argv[index]

    customization.enable_vt100()

    online_check.init_is_online()

    main_logic.init_thread_system()
    check_generate_wrapper()
    check_settings()

    if settings.settings_information.init_settings_done:
        uproject_check()
        uproject_file = settings.get_uproject_file()
        if uproject_file and uproject_file.exists():
            if not is_assign_chunk_id_warning_being_suppressed():
                assign_chunk_id_usage_check()
        unreal_engine_check()
        game_launcher_exe_override_check()
        # git_info_check()
        # repak.ensure_repak_installed()
        # retoc.ensure_retoc_installed()
        # game_exe_check()

        # if repak.get_is_using_repak_path_override():
        #     file_io.check_file_exists(repak.get_repak_path_override())
        #     logger.log_message("Check: Repak exists")

        # if retoc.get_is_using_retoc_path_override():
        #     file_io.check_file_exists(retoc.get_retoc_path_override())
        #     logger.log_message("Check: Retoc exists")

        logger.log_message("Check: Game exists")

        logger.log_message("Check: Passed all init checks")

    clear_temp_dir()

    cache.logging_function = logger.log_message
    cache._cache_dir = settings.settings_information.settings.get("cache", {}).get("cache_dir", None)
    cache.SCRIPT_DIR = file_io.SCRIPT_DIR
    cache.is_online = online_check.is_online
    cache.has_inited = True
    cache.settings_information = settings.settings_information
    cache.init_cache()


def check_generate_wrapper() -> None:
    if "--generate_wrapper" in sys.argv:
        wrapper.generate_wrapper()


def check_settings():
    if "--settings_json" in sys.argv:
        index = sys.argv.index("--settings_json") + 1
        if index < len(sys.argv):
            p = sys.argv[index].strip("'").strip('"')
            p = os.path.normpath(p)
            if os.path.isabs(p):
                settings_file = p
            else:
                settings_file = os.path.abspath(p)
            return settings.load_settings(settings_file)
        logger.log_message("Error: No file path provided after --settings_json.")
        sys.exit(1)
    return
