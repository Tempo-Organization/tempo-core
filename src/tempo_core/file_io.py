from questionary import path
import glob
import hashlib
import os
import shutil
import sys
import webbrowser
import zipfile
from pathlib import Path

import requests
from requests.exceptions import HTTPError, RequestException

from tempo_core import logger, online_check

SCRIPT_DIR = (
    Path(sys.executable).parent
    if getattr(sys, "frozen", False)
    else Path(__file__).resolve().parent
)


def unzip_zip(zip_path: Path, output_location: Path) -> None:
    if zip_path.exists():
        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            zip_ref.extractall(output_location)


def download_file(url: str, download_path: Path) -> None:
    if not online_check.is_online:
        raise RuntimeError('You are not able to download files when not connected to the web.')
    try:
        response = requests.get(url, stream=True, timeout=10)
        response.raise_for_status()

        download_path.parent.mkdir(parents=True, exist_ok=True)

        with download_path.open("wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)

        logger.log_message(f"Download completed: {download_path}")

    except HTTPError as http_err:
        logger.log_message(f"HTTP error occurred while downloading {url}: {http_err}")
    except RequestException as req_err:
        logger.log_message(f"Request error occurred while downloading {url}: {req_err}")
    except OSError as io_err:
        logger.log_message(
            f"File I/O error occurred while saving to {download_path}: {io_err}",
        )


def open_dir_in_file_browser(input_directory: Path) -> None:
    formatted_directory = input_directory.absolute()
    if not formatted_directory.is_dir():
        logger.log_message(
            f"Error: The directory '{formatted_directory}' does not exist.",
        )
        return
    os.startfile(formatted_directory)


def open_file_in_default(file_path: Path) -> None:
    os.startfile(file_path)


def open_website(input_url: str) -> None:
    if not online_check.is_online:
        raise RuntimeError('You are not able to open websites in your browser when not connected to the web.')
    webbrowser.open(input_url)


def verify_directory_exists(dir_path: Path) -> bool:
    if dir_path.is_dir():
        return True
    directory_not_found_error = f'Check: "{dir_path}" directory not found.'
    raise NotADirectoryError(directory_not_found_error)


def verify_directories_exists(directory_paths: list[Path]) -> None:
    for directory_path in directory_paths:
        if not directory_path.is_dir():
            directory_not_found_error = (
                f'Check: "{directory_path}" directory not found.'
            )
            raise NotADirectoryError(directory_not_found_error)


def check_path_exists(path: Path) -> bool:
    if path.exists():
        return True
    path_not_found_error = f'Check: "{path}" path is not a directory or file.'
    raise FileNotFoundError(path_not_found_error)


def verify_file_exists(file_path: Path | None) -> bool:
    if not file_path:
        return False
    if file_path.exists():
        return True
    file_not_found_error = f'Check: "{file_path}" file not found.'
    raise FileNotFoundError(file_not_found_error)


def verify_files_exists(file_paths: list[Path]) -> None:
    for file_path in file_paths:
        if not file_path.is_file():
            file_not_found_error = f'Check: "{file_path}" file not found.'
            raise FileNotFoundError(file_not_found_error)


def get_file_hash(file_path: Path) -> str:
    md5 = hashlib.sha256()
    with file_path.open("rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            md5.update(chunk)
    return md5.hexdigest()


def get_do_files_have_same_hash(file_path_one: Path, file_path_two: Path) -> bool:
    if file_path_one.exists() and file_path_two.exists():
        return get_file_hash(file_path_one) == get_file_hash(file_path_two)
    return False


def get_files_in_tree(tree_path: Path) -> list[Path]:
    return list(tree_path.rglob("*"))


def get_file_extension(file_path: Path) -> str:
    return file_path.suffix.lstrip(".")


# returns extension, not .extension (e.g. txt not .txt)
def get_file_extensions(directory_with_base_name: str) -> list[str]:
    p = Path(directory_with_base_name)
    directory = p.parent
    base_name = p.name

    extensions = set()

    for _, _, files in Path.walk(directory):
        for file in files:
            if file.startswith(base_name):
                ext =  Path(file).suffix
                if ext:
                    extensions.add(ext)

    return list(extensions)


def get_files_in_dir(directory: Path) -> list[Path]:
    return [
        f for f in directory.iterdir() if Path(directory / f).is_file()
    ]


def filter_by_extension(files: list[Path], extension: str) -> list[Path]:
    ext = extension if extension.startswith(".") else f".{extension}"
    ext = ext.lower()

    return [f for f in files if f.suffix.lower() == ext]


def get_all_lines_in_config(config_path: Path) -> list[str]:
    with config_path.open(encoding="utf-8") as file:
        return file.readlines()


def set_all_lines_in_config(config_path: Path, lines: list[str]) -> None:
    with config_path.open("w", encoding="utf-8") as file:
        file.writelines(lines)


def add_line_to_config(config_path: Path, line: str) -> None:
    if not does_config_have_line(config_path, line):
        with config_path.open("a", encoding="utf-8") as file:
            file.write(line + "\n")


def remove_line_from_config(config_path: Path, line: str) -> None:
    lines = get_all_lines_in_config(config_path)
    with config_path.open("w", encoding="utf-8") as file:
        file.writelines(
            config_line for config_line in lines if config_line.rstrip("\n") != line
        )


def does_config_have_line(config_path: Path, line: str) -> bool:
    return line + "\n" in get_all_lines_in_config(config_path)


def remove_lines_from_config_that_start_with_substring(
    config_path: Path, substring: str,
) -> None:
    new_lines = []
    for line in get_all_lines_in_config(config_path):
        if not line.startswith(substring):
            new_lines.append(line)
    set_all_lines_in_config(config_path, new_lines)


def remove_lines_from_config_that_end_with_substring(config_path: Path, substring: str) -> None:
    new_lines = []
    for line in get_all_lines_in_config(config_path):
        if not line.endswith(substring):
            new_lines.append(line)
    set_all_lines_in_config(config_path, new_lines)


def remove_lines_from_config_that_contain_substring(config_path: Path, substring: str) -> None:
    new_lines = []
    for line in get_all_lines_in_config(config_path):
        if line not in (substring):
            new_lines.append(line)
    set_all_lines_in_config(config_path, new_lines)


def get_platform_wrapper_extension() -> str:
    return "bat" if os.name == "nt" else "sh"

# maybe fix, idk might be needed
def ensure_path_quoted(path: str) -> str:
    return f'"{path}"' if not path.startswith('"') and not path.endswith('"') else path


def zip_directory_tree(input_dir: Path, output_dir: Path, zip_name: str = "archive.zip") -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    zip_path = (output_dir / zip_name).resolve()

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        for file_path in input_dir.rglob("*"):
            if not file_path.is_file():
                continue

            file_path = file_path.resolve()

            if file_path == zip_path:
                continue

            arcname = file_path.relative_to(input_dir)
            zipf.write(file_path, arcname)

    logger.log_message(f"Directory tree zipped successfully: {zip_path}")


def move(input_path: Path, output_path: Path, overwrite: bool) -> None:
    if input_path == output_path:
        logger.log_message("Error: Input and output paths must be different.")
        raise RuntimeError

    if (
        input_path.is_dir()
        and output_path.is_dir()
        and output_path in input_path.parents
    ):
        logger.log_message("Error: Cannot move a directory inside itself.")
        raise RuntimeError

    if output_path.exists():
        if not overwrite:
            logger.log_message(
                f"Error: {output_path} already exists. Use --overwrite to replace.",
            )
            raise RuntimeError
        if output_path.is_dir():
            output_path = output_path / input_path.name

    shutil.move(str(input_path), str(output_path))
    logger.log_message(f"Successfully moved {input_path} to {output_path}")


def copy(input_path: Path, output_path: Path, *, overwrite: bool) -> None:
    if input_path == output_path:
        logger.log_message("Error: Input and output paths must be different.")
        raise RuntimeError

    if (
        input_path.is_dir()
        and output_path.is_dir()
        and output_path in input_path.parents
    ):
        logger.log_message("Error: Cannot copy a directory inside itself.")
        raise RuntimeError

    if output_path.exists():
        if not overwrite:
            logger.log_message(
                f"Error: {output_path} already exists. Use --overwrite to replace.",
            )
            raise RuntimeError
        if output_path.is_dir():
            output_path = output_path / input_path.name

    if input_path.is_dir():
        shutil.copytree(str(input_path), str(output_path), dirs_exist_ok=overwrite)
    else:
        shutil.copy2(str(input_path), str(output_path))

    logger.log_message(f"Successfully copied {input_path} to {output_path}")


def symlink(input_path: Path, output_path: Path, overwrite: bool) -> None:
    if output_path.exists():
        if not overwrite:
            logger.log_message(
                f"Error: {output_path} already exists. Use --overwrite to replace.",
            )
            raise RuntimeError
        if output_path.is_dir():
            output_path.rmdir()
        else:
            output_path.unlink()
    try:
        input_path.symlink_to(output_path)
        logger.log_message(
            f"Successfully created symlink: {output_path} -> {input_path}",
        )
    except OSError as e:
        logger.log_message(f"Error: Failed to create symlink: {e}")
        raise RuntimeError(f"Failed to create symlink: {e}") from e


def delete(input_paths: list[Path]) -> None:
    for path in input_paths:
        if not path.exists():
            logger.log_message(f"Error: {path} does not exist.")
            raise RuntimeError

        if path.is_dir():
            for item in path.iterdir():
                item.unlink() if item.is_file() else delete([item])
            path.rmdir()
        else:
            path.unlink()
        logger.log_message(f"Successfully deleted {path}")
