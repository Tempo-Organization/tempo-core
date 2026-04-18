from __future__ import annotations

import os
import subprocess

from tempo_core import file_io, logger
from tempo_core.data_structures import ExecutionMode
import tempo_core.settings


def run_app(
    exe_path: str,
    exec_mode: ExecutionMode = ExecutionMode.SYNC,
    args: list[str] | None = None,
    temp_dir: str = tempo_core.settings.get_temp_directory(),
) -> None:
    os.makedirs(temp_dir, exist_ok=True)

    if not args:
        args = []
    exe_path = file_io.ensure_path_quoted(exe_path)

    if exec_mode == ExecutionMode.SYNC:
        command = exe_path
        for arg in args:
            command = f"{command} {arg}"
        logger.log_message("----------------------------------------------------")
        logger.log_message(f"Command: main executable: {exe_path}")
        for arg in args:
            logger.log_message(f"Command: arg: {arg}")
        logger.log_message("----------------------------------------------------")
        logger.log_message(f"Command: {command} running with the {exec_mode} enum")
        os.makedirs(temp_dir, exist_ok=True)
        if temp_dir and os.path.isdir(temp_dir):
            os.chdir(temp_dir)

        process = subprocess.Popen(
            command,
            cwd=temp_dir,
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
        command = exe_path
        for arg in args:
            command = f"{command} {arg}"
        logger.log_message(f"Command: {command} started with the {exec_mode} enum")
        subprocess.Popen(command, cwd=temp_dir, start_new_session=True)
