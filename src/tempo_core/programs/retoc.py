import os
import sys
import shutil
import pathlib
import subprocess
import platform

import requests

from tempo_core import logger, settings, data_structures, utilities, cache
from tempo_core.programs import unreal_pak, unreal_engine


def get_current_retoc_release_tag() -> str:

    default_value = "latest"
    config_value = None

    if settings.settings_information.settings:
        config_value = settings.settings_information.settings.get('retoc_info', {}).get('retoc_release_tag')

    env_value = os.environ.get('TEMPO_RETOC_RELEASE_TAG')

    cli_value = None
    if '--retoc-release-tag' in sys.argv:
        idx = sys.argv.index('--retoc-release-tag')
        if idx + 1 < len(sys.argv):
            cli_value = sys.argv[idx + 1]
        else:
            raise RuntimeError('You passed --retoc-release-tag without a tag after it.')

    prioritized_value = cli_value or env_value or config_value or default_value

    if prioritized_value == "latest":
        try:
            response = requests.get("https://api.github.com/repos/trumank/retoc/releases/latest", timeout=5)
            response.raise_for_status()
            return response.json().get("tag_name", "latest")
        except Exception as e:
            print(f"[Warning] Failed to fetch latest Retoc release tag from GitHub: {e}")
            return "latest"

    return prioritized_value


def get_tool_install_dir(tool_name: str) -> str:
    if settings.is_windows():
        platform_name = 'windows'
    elif settings.is_linux():
        platform_name = 'linux'
    else:
        raise RuntimeError('You are on an unsupported os')
    return os.path.normpath(os.path.join(
        cache.get_cache_dir(), "tools", tool_name, platform_name, get_current_retoc_release_tag()
    ))


def get_executable_name() -> str:
    if settings.is_windows():
        return 'retoc.exe'
    elif settings.is_linux():
        return 'retoc'
    else:
        raise ValueError('unsupported os')


def get_retoc_directory() -> str:
    
    default_value = get_tool_install_dir('retoc')

    config_value = None
    if settings.settings_information.settings:
        config_value = settings.settings_information.settings.get('retoc_info', {}).get('retoc_dir', None)

    env_value = os.environ.get('TEMPO_RETOC_DIR')

    cli_value = None
    if '--retoc-dir' in sys.argv:
        idx = sys.argv.index('--retoc-dir')
        if idx + 1 < len(sys.argv):
            cli_value = sys.argv[idx + 1]
        else:
            raise RuntimeError('you passed --retoc-dir without a tag after')
    
    prioritized_value = cli_value or env_value or config_value or default_value

    return prioritized_value


def get_retoc_package_path():
    return os.path.normpath(f'{get_retoc_directory()}/{get_executable_name()}')


def run_retoc_to_zen_command(input_directory: pathlib.Path, output_utoc: pathlib.Path, unreal_version: data_structures.UnrealEngineVersion) -> list[pathlib.Path]:
    if not pathlib.Path.is_dir(input_directory):
        raise NotADirectoryError(f'Input directory "{input_directory}" does not exist.') 
    
    print(unreal_version.get_retoc_unreal_version_str())
    
    command = [
        get_retoc_package_path(),
        "to-zen",
        input_directory,
        output_utoc,
        "--version",
        unreal_version.get_retoc_unreal_version_str()
    ]
    subprocess.run(command)

    output_pak = pathlib.Path(f'{os.path.splitext(output_utoc)[0]}.pak')
    output_ucas = pathlib.Path(f'{os.path.splitext(output_utoc)[0]}.ucas')
    file_paths = [
        output_pak,
        output_ucas,
        pathlib.Path(output_utoc)
    ]

    missing_files = [f for f in file_paths if not f.exists()]
    if missing_files:
        raise FileNotFoundError(f"Missing output files: {missing_files}")
    
    return file_paths


def make_retoc_mod(
    mod_name: str, final_pak_file: str, *, use_symlinks: bool
):
    from tempo_core import packing
    old_ucas = pathlib.Path(f'{os.path.splitext(final_pak_file)[0]}.ucas')
    old_utoc = pathlib.Path(f'{os.path.splitext(final_pak_file)[0]}.utoc')
    old_file_paths = [
        old_utoc,
        old_ucas,
        pathlib.Path(final_pak_file)
    ]

    for file in old_file_paths:
        if pathlib.Path.is_file(file):
            pathlib.Path.unlink(file)

    original_mod_dir = unreal_pak.get_pak_dir_to_pack(mod_name)
    original_mod_base_dir = os.path.dirname(original_mod_dir)
    ucas_mod_dir = os.path.normpath(f'{original_mod_base_dir}/{mod_name}_ucas')

    os.makedirs(ucas_mod_dir, exist_ok=True)

    ucas_extensions = {'.umap', '.uexp', '.uptnl', '.ubulk', '.uasset', '.ushaderbytecode'}

    for root, _, files in os.walk(original_mod_dir):
        for file in files:
            source_path = os.path.join(root, file)
            rel_path = os.path.relpath(source_path, original_mod_dir)
            ext = os.path.splitext(file)[1].lower()

            if ext in ucas_extensions:
                target_path = os.path.join(ucas_mod_dir, rel_path)
                os.makedirs(os.path.dirname(target_path), exist_ok=True)
                shutil.move(source_path, target_path)

    if any(files for _, _, files in os.walk(ucas_mod_dir)):
        run_retoc_to_zen_command(
            input_directory=pathlib.Path(ucas_mod_dir),
            output_utoc=pathlib.Path(f'{os.path.splitext(final_pak_file)[0]}.utoc'),
            unreal_version=settings.get_unreal_engine_version(settings.get_unreal_engine_dir())
        )

    packing.make_pak_repak(mod_name=mod_name, use_symlinks=use_symlinks)


def get_file_to_download() -> str:
    if settings.is_windows():
        return 'retoc_cli-x86_64-pc-windows-msvc.zip'
    elif settings.is_linux():
        return 'retoc-x86_64-unknown-linux-gnu.tar.xz'
    else:
        raise ValueError('unsupported os')


def get_download_url() -> str:
    base_url_prefix = f'https://github.com/trumank/retoc/releases/download/{get_current_retoc_release_tag()}/retoc-x86_64-'
    if settings.is_windows():
        return f'{base_url_prefix}pc-windows-msvc.zip'
    elif settings.is_linux():
        return f'{base_url_prefix}unknown-linux-gnu.tar.xz'
    else:
        raise ValueError('unsupported os')


def install_tool_retoc():
    cache.install_tool_to_cache(
        tools = cache.TempoCache, 
        tool_name = 'retoc', 
        version_tag = get_current_retoc_release_tag(), 
        file_paths = [], 
        executable_path = get_executable_name(), 
        file_to_download = get_file_to_download(), 
        download_url = get_download_url()
    )


def install_retoc_mod(*, mod_name: str, use_symlinks: bool):
    retoc_path = get_retoc_package_path()
    if not os.path.isfile(retoc_path):
        install_tool_retoc()
        if not os.path.isfile(retoc_path):
            no_repak_error_message = f'retoc was not found at the following location "{retoc_path}"'
            raise FileNotFoundError(no_repak_error_message)
    unreal_pak.move_files_for_packing(mod_name)
    output_pak_dir = f"{settings.get_working_dir()}/{utilities.get_pak_dir_structure(mod_name)}"
    final_pak_file = f"{utilities.custom_get_game_paks_dir()}/{utilities.get_pak_dir_structure(mod_name)}/{mod_name}.pak"
    os.makedirs(output_pak_dir, exist_ok=True)
    os.makedirs(
        f"{utilities.custom_get_game_paks_dir()}/{utilities.get_pak_dir_structure(mod_name)}",
        exist_ok=True,
    )
    make_retoc_mod(mod_name, final_pak_file, use_symlinks=use_symlinks)
