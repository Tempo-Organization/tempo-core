import os
import shutil
import pathlib
import subprocess
import platform

import requests

from tempo_core import logger, settings, data_structures, utilities
from tempo_core.programs import unreal_pak, unreal_engine


def get_is_using_retoc_path_override() -> bool:
    return settings.settings_information.settings.get("retoc_info", {}).get("override_default_retoc_path", False)


def get_retoc_path_override() -> str:
    return settings.settings_information.settings["retoc_info"]["retoc_path_override"]


def get_retoc_package_path():
    if get_is_using_retoc_path_override():
        return get_retoc_path_override()
    return os.path.join(os.path.expanduser("~"), ".cargo", "bin", "retoc.exe")


def download_and_install_latest_version(repository="trumank/retoc", install_path=None):
    if install_path is None:
        install_path = os.path.join(os.path.expanduser("~"), ".cargo", "bin")

    api_url = f"https://api.github.com/repos/{repository}/releases/latest"

    try:
        response = requests.get(api_url)
        response.raise_for_status()
        release_data = response.json()

        # Always use the PowerShell installer
        script_name = "retoc-installer.ps1"
        script_path = os.path.join(os.environ.get("TEMP", "/tmp"), script_name)

        asset = next(
            (asset for asset in release_data["assets"] if asset["name"] == script_name),
            None,
        )

        if asset is None:
            raise RuntimeError(f'Asset "{script_name}" not found in the latest release.')

        asset_url = asset["browser_download_url"]
        script_response = requests.get(asset_url)
        script_response.raise_for_status()

        with open(script_path, "wb") as file:
            file.write(script_response.content)

        # Determine PowerShell executable
        powershell_exe = shutil.which("powershell") or shutil.which("pwsh")
        if not powershell_exe:
            raise FileNotFoundError("PowerShell executable not found (tried 'powershell' and 'pwsh').")

        subprocess.run(
            [
                powershell_exe,
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                script_path,
            ],
            check=True,
        )

        logger.log_message("Retoc CLI installed successfully.")

    except requests.RequestException as e:
        logger.log_message(f"Error fetching release information: {e}")
    except subprocess.CalledProcessError as e:
        logger.log_message(f"Error executing the installer script: {e}")
    except Exception as e:
        logger.log_message(f"Unexpected error: {e}")


def ensure_retoc_installed():
    retoc_path = get_retoc_package_path()

    if os.path.exists(retoc_path):
        logger.log_message(
            f"Retoc is already installed at {retoc_path}. Skipping installation."
        )
        return

    logger.log_message("Retoc executable not found. Proceeding with installation...")

    download_and_install_latest_version()


# try to use the one from the dataclass when possible, this will bwe deprecated
def get_retoc_version_str_from_engine_version(engine_version: str) -> str:
    # takes in a string like 5.3 or 4.27 and returns a string like UE5_3 or UE4_27
    parts = engine_version.strip().split(".")
    return f'UE{parts[0]}_{parts[1]}' if len(parts) > 1 else f'UE{parts[0]}'



def get_retoc_pak_version_str() -> str:
    # the below code is because we either derive the version from the engine version
    # if not using engine, it can't be derived from the engine, so we need to manually specify
    if settings.get_is_overriding_automatic_version_finding():
        retoc_version_str = settings.settings_information.settings["retoc_info"][
            "retoc_version"
        ]
    else:
        # have this use the data class later
        retoc_version_str = get_retoc_version_str_from_engine_version(settings.custom_get_unreal_engine_version(settings.get_unreal_engine_dir()))
    return retoc_version_str


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


def make_iostore_unreal_pak_mod(
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

    # try:
    #     os.rmdir(original_mod_dir)
    # except OSError:
    #     pass

    ue_version_str = settings.custom_get_unreal_engine_version(settings.get_unreal_engine_dir())
    major_str, minor_str = ue_version_str.split(".")
    unreal_version = data_structures.UnrealEngineVersion(major_version=int(major_str), minor_version=int(minor_str))
    if any(files for _, _, files in os.walk(ucas_mod_dir)):
        run_retoc_to_zen_command(
            input_directory=pathlib.Path(ucas_mod_dir),
            output_utoc=pathlib.Path(f'{os.path.splitext(final_pak_file)[0]}.utoc'),
            unreal_version=unreal_version
        )

    packing.make_pak_repak(mod_name=mod_name, use_symlinks=use_symlinks)


def install_retoc_mod(*, mod_name: str, compression_type: data_structures.CompressionType, use_symlinks: bool):
    unreal_pak.move_files_for_packing(mod_name)
    compression_str = data_structures.CompressionType(compression_type).value
    output_pak_dir = f"{settings.get_working_dir()}/{utilities.get_pak_dir_structure(mod_name)}"
    intermediate_pak_file = f"{settings.get_working_dir()}/{utilities.get_pak_dir_structure(mod_name)}/{mod_name}.pak"
    final_pak_file = f"{utilities.custom_get_game_paks_dir()}/{utilities.get_pak_dir_structure(mod_name)}/{mod_name}.pak"
    os.makedirs(output_pak_dir, exist_ok=True)
    os.makedirs(
        f"{utilities.custom_get_game_paks_dir()}/{utilities.get_pak_dir_structure(mod_name)}",
        exist_ok=True,
    )
    make_iostore_unreal_pak_mod(mod_name, final_pak_file, use_symlinks=use_symlinks)


# make a reusable platform function
# get the latest tag
# get the platform
# get the cache dir
# if alreayd installed check the install is still valid and if so use that, otherwise download a new one into the cahce
# 