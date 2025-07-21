import os
import sys
from enum import Enum
from typing import cast

import requests

from tempo_core import settings, app_runner, utilities, cache, data_structures


class RepakCompressionType(Enum):
    """
    enum for the types of repak pack commamd compression
    """

    NONE = "None"
    ZLIB = "Zlib"
    GZIP = "Gzip"
    OODLE = "Oodle"
    ZSTD = "Zstd"


def get_repak_package_path():
    return os.path.normpath(f'{get_repak_directory()}/{get_executable_name()}')


def get_current_repak_release_tag() -> str:

    default_value = "latest"
    config_value = None

    if settings.settings_information.settings:
        config_value = settings.settings_information.settings.get('repak_info', {}).get('repak_release_tag')

    env_value = os.environ.get('TEMPO_REPAK_RELEASE_TAG')

    cli_value = None
    if '--repak-release-tag' in sys.argv:
        idx = sys.argv.index('--repak-release-tag')
        if idx + 1 < len(sys.argv):
            cli_value = sys.argv[idx + 1]
        else:
            raise RuntimeError('You passed --repak-release-tag without a tag after it.')

    prioritized_value = cli_value or env_value or config_value or default_value

    if prioritized_value == "latest":
        try:
            response = requests.get("https://api.github.com/repos/trumank/repak/releases/latest", timeout=5)
            response.raise_for_status()
            return response.json().get("tag_name", "latest")
        except Exception as e:
            print(f"[Warning] Failed to fetch latest Repak release tag from GitHub: {e}")
            return "latest"

    return prioritized_value


def get_executable_name() -> str:
    if settings.is_windows():
        return 'repak.exe'
    elif settings.is_linux():
        return 'repak'
    else:
        raise ValueError('unsupported os')


def get_file_to_download() -> str:
    if settings.is_windows():
        return 'repak_cli-x86_64-pc-windows-msvc.zip'
    elif settings.is_linux():
        return 'repak_cli-x86_64-unknown-linux-gnu.tar.xz'
    else:
        raise ValueError('unsupported os')


def get_download_url() -> str:
    base_url_prefix = f'https://github.com/trumank/repak/releases/download/{get_current_repak_release_tag()}/repak_cli-x86_64-'
    if settings.is_windows():
        return f'{base_url_prefix}pc-windows-msvc.zip'
    elif settings.is_linux():
        return f'{base_url_prefix}unknown-linux-gnu.tar.xz'
    else:
        raise ValueError('unsupported os')


def install_tool_repak():
    cache.install_tool_to_cache(
        tools = cache.TempoCache, 
        tool_name = 'repak', 
        version_tag = get_current_repak_release_tag(), 
        file_paths = [], 
        executable_path = get_executable_name(), 
        file_to_download = get_file_to_download(), 
        download_url = get_download_url()
    )
    

def run_repak_pack_command(input_directory: str, output_pak_file: str):
    repak_path = get_repak_package_path()
    if not os.path.isfile(repak_path):
        install_tool_repak()
        if not os.path.isfile(repak_path):
            no_repak_error_message = f'repak was not found at the following location "{repak_path}"'
            raise FileNotFoundError(no_repak_error_message)
    command = f'"{repak_path}" pack "{input_directory}" "{output_pak_file}"'
    compression_type_str = settings.settings_information.settings.get('repak_info', {}).get('repak_compression_type', None)
    if compression_type_str:
        command = f"{command} --compression {compression_type_str}"
    # when not manually overriding, check the toml for unreal version, before getting it from the engine directory
    default = settings.get_unreal_engine_version(settings.get_unreal_engine_dir()).get_repak_unreal_version_str()
    command = f"{command} --version {settings.settings_information.settings.get("repak_info", {}).get("repak_version", default)}"
    app_runner.run_app(command)


def get_repak_compression_type() -> RepakCompressionType:
    default_value = "None"

    config_value = None
    if settings.settings_information.settings:
        config_value = settings.settings_information.settings.get('repak_info', {}).get('repak_compression_type', None)

    env_value = os.environ.get('TEMPO_REPAK_COMPRESSION_TYPE')

    cli_value = None
    if '--repak-compression-type' in sys.argv:
        idx = sys.argv.index('--repak-compression-type')
        if idx + 1 < len(sys.argv):
            cli_value = sys.argv[idx + 1]
        else:
            raise RuntimeError('you passed --repak-compression-type without a compression type after')
    valid_values = data_structures.get_enum_strings_from_enum(RepakCompressionType)

    if cli_value is not None and cli_value not in valid_values:
        raise ValueError(f'Invalid CLI value: {cli_value}. Must be one of {valid_values}.')

    if env_value is not None and env_value not in valid_values:
        raise ValueError(f'Invalid environment variable value: {env_value}. Must be one of {valid_values}.')

    if config_value is not None and config_value not in valid_values:
        raise ValueError(f'Invalid config file value: {config_value}. Must be one of {valid_values}.')

    if default_value is not None and default_value not in valid_values:
        raise ValueError(f'Invalid default value: {default_value}. Must be one of {valid_values}.')
    
    prioritized_value = cli_value or env_value or config_value or default_value

    return cast(RepakCompressionType, data_structures.get_enum_from_val(RepakCompressionType, prioritized_value))


def get_repak_pack_version() -> str:
    # finish this to do
    # have it first try and get it all three non default ways, and if not possible then get version directly from the toml, then check engine, then throw error otherwise
    unreal_version = settings.get_unreal_engine_version(settings.get_unreal_engine_dir())

    default_value = unreal_version.get_repak_unreal_version_str()

    config_value = None
    if settings.settings_information.settings:
        config_value = settings.settings_information.settings.get('repak_info', {}).get('repak_pack_version', None)

    env_value = os.environ.get('TEMPO_REPAK_PACK_VERSION')

    cli_value = None
    if '--repak-pack-version' in sys.argv:
        idx = sys.argv.index('--repak-pack-version')
        if idx + 1 < len(sys.argv):
            cli_value = sys.argv[idx + 1]
        else:
            raise RuntimeError('you passed --repak-pack-version without a version after')
    valid_values = data_structures.UnrealEngineVersion.engine_version_to_repak_version.values()

    if cli_value is not None and cli_value not in valid_values:
        raise ValueError(f'Invalid CLI value: {cli_value}. Must be one of {valid_values}.')

    if env_value is not None and env_value not in valid_values:
        raise ValueError(f'Invalid environment variable value: {env_value}. Must be one of {valid_values}.')

    if config_value is not None and config_value not in valid_values:
        raise ValueError(f'Invalid config file value: {config_value}. Must be one of {valid_values}.')

    if default_value is not None and default_value not in valid_values:
        raise ValueError(f'Invalid default value: {default_value}. Must be one of {valid_values}.')
    
    return cli_value or env_value or config_value or default_value


def is_current_preferred_repak_version_installed() -> bool:
    # this doesn't check the tag like it should
    # Check if the Repak tool is present in the cache and has a valid version
    for tool in cache.TempoCache.tool_entries:
        if tool.get_repo_name().lower() == "repak":
            for entry in tool.cache_entries:
                if entry.is_cache_valid():
                    return True
    return False


def get_repak_tool_entry() -> cache.Tool | None:
    # Return the Repak tool entry if present
    for tool in cache.TempoCache.tool_entries:
        if tool.get_repo_name().lower() == "repak":
            return tool
    print("Repak tool not found in cache. Please install it first.")
    return None


def get_repak_cache_entry_by_tag(tag: str) -> cache.CacheEntry:
    repak_tool = get_repak_tool_entry()
    if not repak_tool:
        raise RuntimeError('invalid repak tool entry')
    for entry in repak_tool.cache_entries:
        if entry.release_tag == tag:
            return entry
    raise RuntimeError(f"Repak cache entry with tag '{tag}' not found.")


def get_tool_install_dir(tool_name: str) -> str:
    if settings.is_windows():
        platform_name = 'windows'
    elif settings.is_linux():
        platform_name = 'linux'
    else:
        raise RuntimeError('You are on an unsupported os')
    return os.path.normpath(os.path.join(
        cache.get_cache_dir(), "tools", tool_name, platform_name, get_current_repak_release_tag()
    ))


def get_repak_directory() -> str:
    
    default_value = get_tool_install_dir('repak')

    config_value = None
    if settings.settings_information.settings:
        config_value = settings.settings_information.settings.get('repak_info', {}).get('repak_dir', None)

    env_value = os.environ.get('TEMPO_REPAK_DIR')

    cli_value = None
    if '--repak-dir' in sys.argv:
        idx = sys.argv.index('--repak-dir')
        if idx + 1 < len(sys.argv):
            cli_value = sys.argv[idx + 1]
        else:
            raise RuntimeError('you passed --repak-dir without a tag after')
    
    prioritized_value = cli_value or env_value or config_value or default_value

    return prioritized_value


    # finish this to do
        
        # default cache dir
        # ['repak_info']['repak_dir']
        # TEMPO_REPAK_DIR
        # --repak-dir
