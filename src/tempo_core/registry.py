import winreg


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
                                    subkey, "InstalledDirectory"
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
            r"SOFTWARE\Epic Games\Unreal Engine\Builds"
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
