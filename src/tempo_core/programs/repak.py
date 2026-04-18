import os
import sys
from enum import Enum

from tempo_core import settings, app_runner, data_structures

from tempo_cache_tools import repak


class RepakCompressionType(Enum):
    """
    enum for the types of repak pack command compression
    """

    NONE = "None"
    ZLIB = "Zlib"
    GZIP = "Gzip"
    OODLE = "Oodle"
    ZSTD = "Zstd"


def run_repak_pack_command(input_directory: str, output_pak_file: str) -> None:
    repak_info = repak.RepakToolInfo()
    repak_path = repak_info.get_executable_path()
    command = f'"{repak_path}" pack "{input_directory}" "{output_pak_file}"'
    compression_type_str = settings.settings_information.settings.get('repak_info', {}).get('repak_compression_type', None)
    if compression_type_str:
        command = f"{command} --compression {compression_type_str}"
    # when not manually overriding, check the toml for unreal version, before getting it from the engine directory
    default = settings.get_unreal_engine_version(str(settings.get_unreal_engine_dir())).get_repak_unreal_version_str() # ty: ignore
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

    return data_structures.get_enum_from_val(RepakCompressionType, prioritized_value)


def get_repak_pack_version() -> str:
    # finish this to do
    # have it first try and get it all three non default ways, and if not possible then get version directly from the toml, then check engine, then throw error otherwise
    unreal_version = settings.get_unreal_engine_version(str(settings.get_unreal_engine_dir()))

    default_value = unreal_version.get_repak_unreal_version_str() # ty: ignore

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
