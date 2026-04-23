import os
import requests
from pathlib import Path

from tempo_core import logger, online_check

default_current_dir = Path.cwd()

def download_files_from_github_repo(
    repo_url: str,
    repo_branch: str = "master",
    file_paths: list[str] | None = None,
    output_directory: Path = default_current_dir,
) -> None:
    if not file_paths or len(file_paths) == 0:
        return
    if not online_check.is_online:
        raise RuntimeError('You are not able to download files from github repos when not connected to the web.')
    try:
        parts = repo_url.strip("/").split("/")
        user, repo = parts[-2], parts[-1]
    except IndexError as err:
        raise ValueError("Invalid GitHub repository URL") from err

    for file_path in file_paths:
        raw_url = (
            f"https://raw.githubusercontent.com/{user}/{repo}/{repo_branch}/{file_path}"
        )
        local_file_path = output_directory / file_path

        try:
            response = requests.get(raw_url)
            response.raise_for_status()
        except requests.RequestException as e:
            logger.log_message(f"Failed to download {file_path}: {e}")
            continue

        local_file_path.parent.mkdir(parents=True, exist_ok=True)
        with local_file_path.open("wb") as f:
            f.write(response.content)
            logger.log_message(f"Downloaded: {file_path} to {local_file_path}")
