import os
import sys
import textwrap
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime
from shutil import get_terminal_size

from tempo_core.console import console
from tempo_core.log_info import LOG_INFO


def get_is_log_file_use_disabled() -> bool:
    return "--disable_log_file_output" in sys.argv


def get_default_log_name_prefix() -> str:
    if "--log_name_prefix" in sys.argv:
        index = sys.argv.index("--log_name_prefix") + 1
        if index < len(sys.argv):
            return sys.argv[index]
    return f"{__name__.split('.')[0]}"


@dataclass
class LogInformation:
    log_base_dir: Path
    log_prefix: str
    has_configured_logging: bool


log_information = LogInformation(
    log_base_dir=Path(Path.cwd() / 'src'),
    log_prefix=get_default_log_name_prefix(),
    has_configured_logging=False,
)


def set_log_base_dir(base_dir: Path) -> None:
    log_information.log_base_dir = base_dir


def configure_logging(
    log_name_prefix: str = get_default_log_name_prefix(),
) -> None:
    log_information.log_prefix = log_name_prefix

    log_dir = Path(log_information.log_base_dir)
    if not log_dir.is_dir():
        log_dir.mkdir(parents=True, exist_ok=True)

    rename_latest_log(log_dir)
    log_information.has_configured_logging = True


def rename_latest_log(log_dir: Path) -> None:
    latest_log_path = Path(log_dir / f"{log_information.log_prefix}_latest.log")
    if latest_log_path.is_file():
        try:
            timestamp = datetime.now().strftime("%m_%d_%Y_%H%M_%S")
            new_name = f"{log_information.log_prefix}_{timestamp}.log"
            new_log_path = Path(log_dir / new_name)

            # Ensure the new log file name is unique
            counter = 1
            while new_log_path.is_file():
                new_name = f"{log_information.log_prefix}_{timestamp}_({counter}).log"
                new_log_path = Path(log_dir / new_name)
                counter += 1

            latest_log_path.rename(new_log_path)

        except PermissionError as e:
            log_message(f"Error renaming log file: {e}")
            return


def log_message(message: str | Path) -> None:
    if isinstance(message, Path):
        message = str(message)
    if log_information.has_configured_logging:
        color_options = LOG_INFO.get("theme_colors", {})
        default_background_color = LOG_INFO.get("background_color", (40, 42, 54))
        default_background_color = f"rgb({default_background_color[0]},{default_background_color[1]},{default_background_color[2]})" # ty: ignore

        default_text_color = LOG_INFO.get("default_color", (94, 94, 255))
        default_text_color = f"rgb({default_text_color[0]},{default_text_color[1]},{default_text_color[2]})" # ty: ignore

        terminal_width = get_terminal_size().columns
        lines = message.splitlines()

        for original_line in lines:
            if not original_line.strip():
                console.print(
                    "".ljust(terminal_width),
                    style=f"{default_text_color} on {default_background_color}",
                    markup=False,
                )
                continue

            wrapped = textwrap.wrap(original_line, width=terminal_width) or [""]

            for line in wrapped:
                padded_line = line.ljust(terminal_width)

                for keyword, color in color_options.items(): # ty: ignore
                    if keyword in original_line:
                        rgb_color = f"rgb({color[0]},{color[1]},{color[2]})"
                        console.print(
                            padded_line,
                            style=f"{rgb_color} on {default_background_color}",
                            markup=False,
                        )
                        break
                else:
                    console.print(
                        padded_line,
                        style=f"{default_text_color} on {default_background_color}",
                        markup=False,
                    )


        log_dir = Path(log_information.log_base_dir)
        log_path = Path(log_dir / f"{log_information.log_prefix}_latest.log")

        if not log_dir.is_dir():
            if not get_is_log_file_use_disabled():
                log_dir.mkdir(parents=True, exist_ok=True)

        if not log_path.is_file():
            try:
                if not get_is_log_file_use_disabled():
                    with log_path.open("w") as log_file:
                        log_file.write("")
            except OSError as e:
                error_color = LOG_INFO.get("error_color", (255, 0, 0))
                error_color = f"rgb({error_color[0]},{error_color[1]},{error_color[2]})" # ty: ignore
                console.print(
                    f"Failed to create log file: {e}",
                    style=f"{error_color} on {default_background_color}",
                    markup=False,
                )
                return

        try:
            if not get_is_log_file_use_disabled():
                with log_path.open("a") as log_file:
                    log_file.write(f"{message}\n")
        except OSError as e:
            error_color = LOG_INFO.get("error_color", (255, 0, 0))
            error_color = f"rgb({error_color[0]},{error_color[1]},{error_color[2]})" # ty: ignore
            console.print(
                f"Failed to write to log file: {e}",
                style=f"{error_color} on {default_background_color}",
                markup=False,
            )
