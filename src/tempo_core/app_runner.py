from __future__ import annotations

import os
import subprocess
from pathlib import Path
from _collections_abc import Sequence

from tempo_core import file_io, logger
from tempo_core.data_structures import ExecutionMode
import tempo_core.settings

default_working_dir = tempo_core.settings.get_temp_directory()

def run_app(
    exe_path: Path,
    exec_mode: ExecutionMode = ExecutionMode.SYNC,
    args: Sequence[str | Path] | None = None,
    working_dir: Path = default_working_dir,
) -> None:
    working_dir.mkdir(parents=True, exist_ok=True)

    if not args:
        args = []
    exe_path_str = file_io.ensure_path_quoted(str(exe_path))

    if exec_mode == ExecutionMode.SYNC:
        command = exe_path_str
        for arg in args:
            command = f"{command} {arg}"
        logger.log_message("----------------------------------------------------")
        logger.log_message(f"Command: main executable: {exe_path_str}")
        for arg in args:
            logger.log_message(f"Command: arg: {arg}")
        logger.log_message("----------------------------------------------------")
        logger.log_message(f"Command: {command} running with the {exec_mode} enum")

        if working_dir and working_dir.is_dir():
            os.chdir(working_dir)

        process = subprocess.Popen(
            command,
            cwd=working_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            shell=True,
        )

        if process.stdout:
            for line in iter(process.stdout.readline, ""):
                logger.log_message(line.strip())

            process.stdout.close()

        process.wait()
        logger.log_message(f"Command: {command} finished")

    elif exec_mode == ExecutionMode.ASYNC:
        command = exe_path_str
        for arg in args:
            command = f"{command} {arg}"
        logger.log_message(f"Command: {command} started with the {exec_mode} enum")
        subprocess.Popen(command, cwd=working_dir, start_new_session=True)
