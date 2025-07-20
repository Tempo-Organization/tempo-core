import os
import sys
import toml
import shutil
import platform
from typing import Optional

import platformdirs

from tempo_core import file_io


def list_tools() -> None:
    # tempo_cli tool list
    return


def uninstall_tool_from_cache() -> None:
    # tempo uninstall tool_name --version version_tag
    return


def install_tool_to_cache() -> None:
    # tempo install tool_name --version version_tag
    return


def clean_cache() -> None:
    # tempo_cli cache clean
    shutil.rmtree(get_cache_dir())


def prune_cache() -> None:
    # tempo_cli cache prune
    return


def print_out_cache_dir() -> None:
    print(get_cache_dir())


def get_tempo_no_cache_env_var_value() -> bool:
    return os.getenv('TEMPO_NO_CACHE', '').lower() in ['1', 'true', 'yes']


def get_tempo_cache_dir_env_var_value() -> Optional[str]:
    return os.getenv('TEMPO_CACHE_DIR')


def was_no_cache_parameter_in_args() -> bool:
    return '--no-cache' in sys.argv


def was_cache_dir_parameter_in_args() -> bool:
    return '--cache-dir' in sys.argv


def get_cache_dir_param_in_args() -> Optional[str]:
    if '--cache-dir' in sys.argv:
        idx = sys.argv.index('--cache-dir')
        if idx + 1 < len(sys.argv):
            return sys.argv[idx + 1]
    return None


def get_default_cache_dir():
    return


def is_cache_dir_in_tempo_config_file(settings_file: str) -> Optional[str]:
    if os.path.exists(settings_file):
        config = toml.load(settings_file)
        value = config.get("cache_dir", "")
        if value == '':
            return False
        else:
            return True
    return False


def get_cache_dir_from_tempo_config_file(settings_file: str) -> Optional[str]:
    return toml.load(settings_file).get("cache_dir")


def get_cache_dir() -> str:
    if get_tempo_no_cache_env_var_value() or was_no_cache_parameter_in_args():
        return get_local_cache_dir_path()

    if was_cache_dir_parameter_in_args():
        param_dir = get_cache_dir_param_in_args()
        if param_dir:
            return os.path.normpath(f"{param_dir}")

    env_dir = get_tempo_cache_dir_env_var_value()
    if env_dir:
        return os.path.normpath(f"{env_dir}")

    config_dir = get_cache_dir_from_tempo_config_file()
    if config_dir:
        return os.path.normpath(f"{config_dir}")

    return os.path.normpath(f"{platformdirs.user_cache_dir('tempo')}")


def get_main_cache_settings_file() -> str:
    return os.path.normpath(f"{get_cache_dir()}/cache.toml")


def get_local_cache_dir_path() -> str:
    return os.path.normpath(f"{file_io.SCRIPT_DIR}/tempo_cache")


def init_cache() -> None:
    cache_path = get_cache_dir()
    if not os.path.exists(cache_path):
        os.makedirs(cache_path)
