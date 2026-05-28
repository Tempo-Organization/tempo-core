import itertools
import winreg
import pathlib


def get_unreal_installs_from_registry() -> dict[str, str]:
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
                                installs[subkey_name] = install_dir
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
                    name, value, _ = winreg.EnumValue(root, i)
                    i += 1
                    installs[name] = value
                except OSError:
                    break
    except FileNotFoundError:
        pass

    return installs


import os
import winreg


def remove_invalid_unreal_engine_registry_entries() -> None:
    def is_valid_install(path: pathlib.Path) -> bool:
        if not path.is_dir():
            return False
        for _, _, files in path.walk():
            if any(f.lower().endswith(".exe") for f in files):
                return True
        return False

    unreal_installs = get_unreal_installs_from_registry()

    # Machine-wide installs
    machine_paths = [
        r"SOFTWARE\EpicGames\Unreal Engine",
        r"SOFTWARE\WOW6432Node\EpicGames\Unreal Engine",
    ]

    for reg_path in machine_paths:
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, reg_path, 0, winreg.KEY_ALL_ACCESS) as root:
                i = 0
                while True:
                    try:
                        subkey_name = winreg.EnumKey(root, i)
                        with winreg.OpenKey(root, subkey_name) as subkey:
                            try:
                                install_dir, _ = winreg.QueryValueEx(subkey, "InstalledDirectory")
                                if not is_valid_install(install_dir):
                                    winreg.DeleteKey(root, subkey_name)
                                    continue  # don't increment i after deletion
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
                    name, value, _ = winreg.EnumValue(root, i)
                    if not is_valid_install(value):
                        winreg.DeleteValue(root, name)
                        continue  # don't increment i after deletion
                    i += 1
                except OSError:
                    break
    except FileNotFoundError:
        pass
