import os
import sys
import pathlib
import requests

from tempo_core import settings, cache, logger


def get_github_cli_package_path():
    return os.path.normpath(f'{get_github_cli_directory()}/{get_executable_name()}')


def get_current_github_cli_release_tag() -> str:

    default_value = "latest"
    config_value = None

    if settings.settings_information.settings:
        config_value = settings.settings_information.settings.get('github_cli_info', {}).get('github_cli_release_tag')

    env_value = os.environ.get('TEMPO_GITHUB_CLI_RELEASE_TAG')

    cli_value = None
    if '--github_cli-release-tag' in sys.argv:
        idx = sys.argv.index('--github_cli-release-tag')
        if idx + 1 < len(sys.argv):
            cli_value = sys.argv[idx + 1]
        else:
            raise RuntimeError('You passed --github_cli-release-tag without a tag after it.')

    prioritized_value = cli_value or env_value or config_value or default_value

    if prioritized_value == "latest":
        try:
            response = requests.get("https://api.github.com/repos/cli/cli/releases/latest", timeout=5)
            response.raise_for_status()
            return response.json().get("tag_name", "latest")
        except Exception as e:
            logger.log_message(f"[Warning] Failed to fetch latest github cli release tag from GitHub: {e}")
            return "latest"

    return prioritized_value


def get_executable_name() -> str:
    if settings.is_windows():
        return 'gh.exe'
    elif settings.is_linux():
        return 'gh'
    else:
        raise ValueError('unsupported os')


def get_file_to_download() -> str:
    if settings.is_windows():
        return f'gh_{get_current_github_cli_release_tag()[1:]}_windows_amd64.zip'
    elif settings.is_linux():
        return f'gh_{get_current_github_cli_release_tag()[1:]}_linux_amd64.tar.gz'
    else:
        raise ValueError('unsupported os')


def get_download_url() -> str:
    base_url_prefix = f'https://github.com/cli/cli/releases/download/{get_current_github_cli_release_tag()}/gh_{get_current_github_cli_release_tag()[1:]}_'
    if settings.is_windows():
        return f'{base_url_prefix}windows_amd64.zip'
    elif settings.is_linux():
        return f'{base_url_prefix}linux_amd64.tar.gz'
    else:
        raise ValueError('unsupported os')


def install_tool_github_cli():
    cache.install_tool_to_cache(
        tools = cache.TempoCache,
        tool_name = 'github_cli',
        version_tag = get_current_github_cli_release_tag(),
        file_paths = [],
        executable_path = get_executable_name(),
        file_to_download = get_file_to_download(),
        download_url = get_download_url()
    )


def is_current_preferred_github_cli_version_installed() -> bool:
    preferred_tag = get_current_github_cli_release_tag()

    for tool in cache.TempoCache.tool_entries:
        if tool.get_repo_name().lower() != "github_cli":
            continue

        for entry in tool.cache_entries:
            if (
                entry.release_tag == preferred_tag
                and entry.is_cache_valid()
            ):
                return True

    return False


def get_github_cli_directory() -> pathlib.Path | None:
    default_value = cache.get_tool_install_dir("github_cli", get_current_github_cli_release_tag())

    config_value = None
    if settings.settings_information.settings:
        config_value = settings.settings_information.settings.get("github_cli_info", {}).get(
            "github_cli_dir", None
        )

    env_value = os.environ.get("TEMPO_GITHUB_CLI_DIR")

    cli_value = None
    if "--github_cli-dir" in sys.argv:
        idx = sys.argv.index("--github_cli-dir")
        if idx + 1 < len(sys.argv):
            cli_value = sys.argv[idx + 1]
        else:
            raise RuntimeError("you passed --github_cli-dir without a tag after")

    prioritized_value = cli_value or env_value or config_value or default_value

    if not os.path.isabs(prioritized_value):
        return pathlib.Path(str(settings.settings_information.settings_json_dir.path), prioritized_value).resolve()
    else:
        return pathlib.Path(prioritized_value).resolve()
