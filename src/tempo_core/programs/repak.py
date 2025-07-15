import os
import shutil
import subprocess

import requests

from tempo_core import logger, settings


def is_repak_packing_enum_in_use():
    is_in_use = False
    for entry in settings.get_mods_info_list_from_json():
        if entry["packing_type"] == "repak":
            is_in_use = True
    return is_in_use


def get_is_using_repak_path_override() -> bool:
    return settings.settings_information.settings.get("repak_info", {}).get("override_default_repak_path", False)


def get_repak_path_override() -> str:
    return settings.settings_information.settings["repak_info"]["repak_path_override"]


def get_repak_package_path():
    if get_is_using_repak_path_override():
        return get_repak_path_override()
    return os.path.join(os.path.expanduser("~"), ".cargo", "bin", "repak.exe")


def download_and_install_latest_version(repository="trumank/repak", install_path=None):
    if install_path is None:
        install_path = os.path.join(os.path.expanduser("~"), ".cargo", "bin")

    api_url = f"https://api.github.com/repos/{repository}/releases/latest"

    try:
        response = requests.get(api_url)
        response.raise_for_status()
        release_data = response.json()

        asset = next(
            (
                asset
                for asset in release_data["assets"]
                if asset["name"] == "repak_cli-installer.ps1"
            ),
            None,
        )

        if asset is None:
            installer_not_found_error = (
                'Asset "repak_cli-installer.ps1" not found in the latest release.'
            )
            raise RuntimeError(installer_not_found_error)

        asset_url = asset["browser_download_url"]
        script_path = os.path.join(os.environ["TEMP"], "repak_cli-installer.ps1")
        script_response = requests.get(asset_url)
        script_response.raise_for_status()

        with open(script_path, "wb") as file:
            file.write(script_response.content)

        # test later the below function works
        # from tempo import utilities
        # exe = 'powershell.exe'
        # args = [
        #     '-ExecutionPolicy',
        #     'Bypass',
        #     '-File',
        #     'script_path'
        # ]
        # utilities.run_app(exe_path=exe, args=args)
        powershell_exe = shutil.which("powershell")
        if not powershell_exe:
            powershell_not_found_error = "Was unable to find powershell"
            raise FileNotFoundError(powershell_not_found_error)
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

        logger.log_message("Repak CLI installed successfully.")

    except requests.RequestException as e:
        logger.log_message(f"Error fetching release information: {e}")
    except subprocess.CalledProcessError as e:
        logger.log_message(f"Error executing the installer script: {e}")


def ensure_repak_installed():
    repak_path = get_repak_package_path()

    if os.path.exists(repak_path):
        logger.log_message(
            f"Repak is already installed at {repak_path}. Skipping installation."
        )
        return

    logger.log_message("Repak executable not found. Proceeding with installation...")

    download_and_install_latest_version()


def get_repak_version_str_from_engine_version() -> str:
    engine_version_to_repack_version = {
        "4.0": "V1",
        "4.1": "V1",
        "4.2": "V1",
        "4.3": "V3",
        "4.4": "V3",
        "4.5": "V3",
        "4.6": "V3",
        "4.7": "V3",
        "4.8": "V3",
        "4.9": "V3",
        "4.10": "V3",
        "4.11": "V3",
        "4.12": "V3",
        "4.13": "V3",
        "4.14": "V3",
        "4.15": "V3",
        "4.16": "V4",
        "4.17": "V4",
        "4.18": "V4",
        "4.19": "V4",
        "4.20": "V5",
        "4.21": "V7",
        "4.22": "V8A",
        "4.23": "V8B",
        "4.24": "V8B",
        "4.25": "V9",
        "4.26": "V11",
        "4.27": "V11",
        "4.28": "V11",
        "5.0": "V11",
        "5.1": "V11",
        "5.2": "V11",
        "5.3": "V11",
        "5.4": "V11",
        "5.5": "V11",
        "5.6": "V11",
    }
    return engine_version_to_repack_version[
        settings.custom_get_unreal_engine_version(settings.get_unreal_engine_dir())
    ]


def get_repak_pak_version_str() -> str:
    # the below code is because we either derive the version from the engine version
    # if not using engine, it can't be derived from the engine, so we need to manually specify
    if settings.get_is_overriding_automatic_version_finding():
        repak_version_str = settings.settings_information.settings["repak_info"][
            "repak_version"
        ]
    else:
        repak_version_str = get_repak_version_str_from_engine_version()
    return repak_version_str
