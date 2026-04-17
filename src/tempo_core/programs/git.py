import os
import requests

from tempo_core import logger, online_check


def download_files_from_github_repo(
    repo_url: str,
    repo_branch: str = "master",
    file_paths: list[str] = [],
    output_directory: str = os.getcwd(),
):
    if not online_check.is_online:
        raise RuntimeError('You are not able to download files from github repos when not connected to the web.')
    try:
        parts = repo_url.strip("/").split("/")
        user, repo = parts[-2], parts[-1]
    except IndexError:
        raise ValueError("Invalid GitHub repository URL")

    for file_path in file_paths:
        raw_url = (
            f"https://raw.githubusercontent.com/{user}/{repo}/{repo_branch}/{file_path}"
        )
        local_file_path = os.path.join(output_directory, file_path)

        try:
            response = requests.get(raw_url)
            response.raise_for_status()
        except requests.RequestException as e:
            logger.log_message(f"Failed to download {file_path}: {e}")
            continue

        os.makedirs(os.path.dirname(local_file_path), exist_ok=True)
        with open(local_file_path, "wb") as f:
            f.write(response.content)
            logger.log_message(f"Downloaded: {file_path} to {local_file_path}")
