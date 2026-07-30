import os
import itertools
import winreg
from pathlib import Path
from uuid import UUID
from dataclasses import replace

from tempo_core.programs import unreal_engine
from tempo_core.data_structures import UnrealEngineVersion
from tempo_core import logger


def get_unreal_installs_from_registry() -> dict[UnrealEngineVersion | UUID, Path]:
    installs = {}

    # Machine-wide installs (Epic Games Launcher)
    machine_paths = [
        r"SOFTWARE\EpicGames\Unreal Engine",
        r"SOFTWARE\WOW6432Node\EpicGames\Unreal Engine",
    ]

    for path in machine_paths:
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, path) as root:
                i = 0
                while True:
                    try:
                        subkey_name = winreg.EnumKey(root, i)
                        i += 1

                        with winreg.OpenKey(root, subkey_name) as subkey:
                            try:
                                install_dir, _ = winreg.QueryValueEx(
                                    subkey, "InstalledDirectory",
                                )
                                unreal_version = UnrealEngineVersion.from_raw_unreal_version_str(subkey_name)
                                install_dir = Path(install_dir)
                                installs[unreal_version] = install_dir
                            except FileNotFoundError:
                                pass
                    except OSError:
                        break
        except FileNotFoundError:
            pass

    # Per-user installs (source/custom builds)
    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"SOFTWARE\Epic Games\Unreal Engine\Builds",
        ) as root:
            i = 0
            while True:
                try:
                    unreal_guid, unreal_engine_directory, _ = winreg.EnumValue(root, i)
                    unreal_engine_directory = Path(unreal_engine_directory)
                    i += 1
                    unreal_version = unreal_engine.get_unreal_engine_version_from_build_version_file(unreal_engine_directory)
                    if unreal_version:
                        unreal_version = replace(unreal_version, guid=UUID(unreal_guid))
                        installs[unreal_version] = unreal_engine_directory
                    else:
                        installs[UUID(unreal_guid)] = unreal_engine_directory
                except OSError:
                    break
    except FileNotFoundError:
        pass

    return installs




def remove_invalid_unreal_engine_registry_entries() -> None:
    # Machine-wide installs
    machine_paths = [
        r"SOFTWARE\EpicGames\Unreal Engine",
        r"SOFTWARE\WOW6432Node\EpicGames\Unreal Engine",
    ]

    for reg_path in machine_paths:
        try:
            with winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                reg_path,
                0,
                winreg.KEY_ALL_ACCESS,
            ) as root:
                i = 0
                while True:
                    try:
                        subkey_name = winreg.EnumKey(root, i)

                        with winreg.OpenKey(root, subkey_name) as subkey:
                            try:
                                install_dir, _ = winreg.QueryValueEx(
                                    subkey,
                                    "InstalledDirectory",
                                )

                                if not Path(install_dir).is_dir():
                                    winreg.DeleteKey(root, subkey_name)
                                    continue  # Don't increment after deletion.
                            except FileNotFoundError:
                                pass

                        i += 1
                    except OSError:
                        break
        except FileNotFoundError:
            pass

    # Per-user installs
    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"SOFTWARE\Epic Games\Unreal Engine\Builds",
            0,
            winreg.KEY_ALL_ACCESS,
        ) as root:
            i = 0
            while True:
                try:
                    guid, install_dir, _ = winreg.EnumValue(root, i)

                    if not Path(install_dir).is_dir():
                        winreg.DeleteValue(root, guid)
                        continue  # Don't increment after deletion.

                    i += 1
                except OSError:
                    break
    except FileNotFoundError:
        pass


def list_unreal_installs(clean: bool) -> None:
    unreal_installs = get_unreal_installs_from_registry()
    if unreal_installs:
        for unreal_version in unreal_installs.keys():
            if isinstance(unreal_version, UnrealEngineVersion):
                unreal_version_str = unreal_version.get_raw_unreal_version_str()
                logger.log_message(f"{unreal_version_str}: {str(unreal_installs[unreal_version])} directory_exists: {unreal_installs[unreal_version].is_dir()}")
            if isinstance(unreal_version, UUID):
                logger.log_message(f"{str(unreal_version)}: {unreal_installs[unreal_version]} directory_exists: {unreal_installs[unreal_version].is_dir()}")

    else:
        logger.log_message('There were no detected unreal engine installs.')
    if clean:
        remove_invalid_unreal_engine_registry_entries()
