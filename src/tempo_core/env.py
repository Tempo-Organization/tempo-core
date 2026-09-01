import os
import winreg
from pathlib import Path

from tempo_core import logger


def env_true(value: str | None) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def getenv(key, default=None) -> (str | None):
    import os
    return os.getenv(key=key, default=default)


def add_path_to_system_environment_path_variable(*paths: Path) -> None:
    resolved_paths = [path.resolve() for path in paths]

    with winreg.OpenKey(
        winreg.HKEY_CURRENT_USER,
        "Environment",
        0,
        winreg.KEY_READ | winreg.KEY_WRITE,
    ) as key:
        try:
            current_path, value_type = winreg.QueryValueEx(key, "Path")
        except FileNotFoundError:
            current_path = ""
            value_type = winreg.REG_EXPAND_SZ

        existing_paths = (
            current_path.split(os.pathsep)
            if current_path
            else []
        )

        existing_normalized = {
            os.path.normcase(os.path.normpath(path))
            for path in existing_paths
            if path
        }

        new_paths = []

        for path in resolved_paths:
            path_string = str(path)
            normalized = os.path.normcase(os.path.normpath(path_string))

            if normalized not in existing_normalized:
                new_paths.append(path_string)
                existing_normalized.add(normalized)

        if new_paths:
            existing_paths.extend(new_paths)

            winreg.SetValueEx(
                key,
                "Path",
                0,
                value_type,
                os.pathsep.join(existing_paths),
            )

    path_message = f"""
    You have added the following path to your system's PATH environmental variable.
    You must close all terminals, and open a new one, before it will be accessible.
    """
    logger.log_message(path_message)