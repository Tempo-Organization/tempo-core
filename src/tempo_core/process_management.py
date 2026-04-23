import os
import shutil
from pathlib import Path
import subprocess

import psutil

from tempo_core import settings
from tempo_core.data_structures import HookStateType
from tempo_core.programs import unreal_engine


def get_process_name(exe_path: Path) -> str:
    return exe_path.name


def is_process_running(process_name: str) -> bool:
    for proc in psutil.process_iter():
        try:
            if process_name.lower() in proc.name().lower():
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    return False


def kill_process(process_name: str) -> None:
    taskkill_path = shutil.which("taskkill")

    if taskkill_path:
        subprocess.run([taskkill_path, "/F", "/IM", process_name], check=False)
    else:
        taskkill_exe_not_found_error = "taskkill.exe not found."
        raise FileNotFoundError(taskkill_exe_not_found_error)


def get_processes_by_substring(substring: str) -> list:
    all_processes = psutil.process_iter(["pid", "name"])
    return [
        proc.info
        for proc in all_processes
        if substring.lower() in proc.info["name"].lower()
    ]


def get_process_kill_events() -> list:
    value_to_return = settings.settings_information.settings["process_kill_events"]["processes"]
    return value_to_return


def kill_processes(state: HookStateType) -> None:
    current_state = state.value if isinstance(state, HookStateType) else state
    for process_info in get_process_kill_events():
        target_state = process_info.get("hook_state")
        if target_state == current_state:
            if process_info["use_substring_check"]:
                proc_name_substring = process_info["process_name"]
                for proc_info in get_processes_by_substring(proc_name_substring):
                    proc_name = proc_info["name"]
                    kill_process(proc_name)
            else:
                proc_name = process_info["process_name"]
                kill_process(proc_name)


def get_game_process_name() -> str:
    return unreal_engine.get_game_process_name(settings.get_game_exe_path()) # ty: ignore


def close_programs(exe_names: list[str]) -> None:
    results = {}

    for exe_name in exe_names:
        found = False
        for proc in psutil.process_iter(["pid", "name"]):
            try:
                if proc.info["name"] and proc.info["name"].lower() == exe_name.lower():
                    proc.terminate()
                    proc.wait(timeout=5)
                    found = True
                    results[exe_name] = "Closed"
                    break
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.TimeoutExpired):
                pass
        if not found:
            results[exe_name] = "Not Found"
