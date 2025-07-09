import os
import shutil

import requests

from tempo_core import file_io, settings


def get_commit_short_hash_from_tag(repo_name, tag_name="latest"):
    """
    Gets the short commit hash (7 characters) for a given tag (default 'latest').

    Args:
        repo_name (str): GitHub repo in 'owner/repo' format.
        tag_name (str): The tag name to fetch the commit hash from.

    Returns:
        str: 7-character short commit hash or an error message.
    """
    try:
        # Get the tag reference
        tag_ref_url = f"https://api.github.com/repos/{repo_name}/git/ref/tags/{tag_name}"
        ref_response = requests.get(tag_ref_url)
        ref_response.raise_for_status()
        tag_ref = ref_response.json()

        # Lightweight tag points directly to a commit
        if tag_ref["object"]["type"] == "commit":
            return tag_ref["object"]["sha"][:7]

        # Annotated tag — follow the tag object
        tag_object_url = tag_ref["object"]["url"]
        tag_object_response = requests.get(tag_object_url)
        tag_object_response.raise_for_status()
        tag_object = tag_object_response.json()

        return tag_object["object"]["sha"][:7]

    except requests.exceptions.RequestException as e:
        return f"Request error: {e}"
    except KeyError:
        return "Tag or commit data not found."


def get_current_tag() -> str:
    return get_commit_short_hash_from_tag('trumank/kismet-analyzer')


def download_kismet_analyzer(output_directory: str):
    url = f"https://github.com/trumank/kismet-analyzer/releases/download/latest/kismet-analyzer-{get_current_tag()}-win-x64.zip"
    download_path = f"{output_directory}/kismet-analyzer-{get_current_tag()}-win-x64.zip"
    file_io.download_file(url, download_path)


def install_kismet_analyzer(output_directory: str):
    os.makedirs(output_directory, exist_ok=True)
    os.makedirs(settings.get_working_dir(), exist_ok=True)
    download_kismet_analyzer(settings.get_working_dir())
    zip_path = f"{settings.get_working_dir()}/kismet-analyzer-{get_current_tag()}-win-x64.zip"
    file_io.unzip_zip(zip_path, output_directory)
    shutil.move(
        f"{output_directory}/kismet-analyzer-{get_current_tag()}-win-x64/kismet-analyzer.exe",
        f"{output_directory}/kismet-analyzer.exe",
    )


def get_kismet_analyzer_path(output_directory: str) -> str:
    return os.path.normpath(f"{output_directory}/kismet-analyzer.exe")


def does_kismet_analyzer_exist(output_directory: str) -> bool:
    return os.path.isfile(get_kismet_analyzer_path(output_directory))
