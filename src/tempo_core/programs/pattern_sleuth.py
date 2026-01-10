import os
import re
import sys
import pathlib
import requests
import subprocess

from tempo_core import settings, cache, logger


def get_patternsleuth_package_path():
    return os.path.normpath(f'{get_patternsleuth_directory()}/{get_executable_name()}')


def get_current_patternsleuth_release_tag() -> str:

    default_value = "latest"
    config_value = None

    if settings.settings_information.settings:
        config_value = settings.settings_information.settings.get('patternsleuth_info', {}).get('patternsleuth_release_tag')

    env_value = os.environ.get('TEMPO_PATTERNSLEUTH_RELEASE_TAG')

    cli_value = None
    if '--patternsleuth-release-tag' in sys.argv:
        idx = sys.argv.index('--patternsleuth-release-tag')
        if idx + 1 < len(sys.argv):
            cli_value = sys.argv[idx + 1]
        else:
            raise RuntimeError('You passed --patternsleuth-release-tag without a tag after it.')

    prioritized_value = cli_value or env_value or config_value or default_value

    if prioritized_value == "latest":
        try:
            response = requests.get("https://api.github.com/repos/Tempo-Organization/patternsleuth/releases/latest", timeout=5)
            response.raise_for_status()
            return response.json().get("tag_name", "latest")
        except Exception as e:
            logger.log_message(f"[Warning] Failed to fetch latest Patternsleuth release tag from GitHub: {e}")
            return "latest"

    return prioritized_value


def get_executable_name() -> str:
    if settings.is_windows():
        return 'patternsleuth.exe'
    elif settings.is_linux():
        return 'patternsleuth'
    else:
        raise ValueError('unsupported os')


def get_file_to_download() -> str:
    if settings.is_windows():
        return 'patternsleuth-x86_64-pc-windows-msvc.zip'
    elif settings.is_linux():
        raise ValueError('unsupported os')
        # return 'repak_cli-x86_64-unknown-linux-gnu.tar.xz'
    else:
        raise ValueError('unsupported os')


def get_download_url() -> str:
    base_url_prefix = f'https://github.com/Tempo-Organization/patternsleuth/releases/download/{get_current_patternsleuth_release_tag()}/patternsleuth-x86_64-'
    if settings.is_windows():
        return f'{base_url_prefix}pc-windows-msvc.zip'
    elif settings.is_linux():
        raise ValueError('unsupported os')
        # return f'{base_url_prefix}unknown-linux-gnu.tar.xz'
    else:
        raise ValueError('unsupported os')


def install_tool_patternsleuth():
    cache.install_tool_to_cache(
        tools = cache.TempoCache,
        tool_name = 'patternsleuth',
        version_tag = get_current_patternsleuth_release_tag(),
        file_paths = [],
        executable_path = get_executable_name(),
        file_to_download = get_file_to_download(),
        download_url = get_download_url()
    )


def is_current_preferred_patternsleuth_version_installed() -> bool:
    # this doesn't check the tag like it should
    # Check if the patternsleuth tool is present in the cache and has a valid version
    for tool in cache.TempoCache.tool_entries:
        if tool.get_repo_name().lower() == "patternsleuth":
            for entry in tool.cache_entries:
                if entry.is_cache_valid():
                    return True
    return False


def get_patternsleuth_tool_entry() -> cache.Tool | None:
    # Return the Patternsleuth tool entry if present
    for tool in cache.TempoCache.tool_entries:
        if tool.get_repo_name().lower() == "patternsleuth":
            return tool
    logger.log_message("Patternsleuth tool not found in cache. Please install it first.")
    return None


def get_patternsleuth_cache_entry_by_tag(tag: str) -> cache.CacheEntry:
    patternsleuth_tool = get_patternsleuth_tool_entry()
    if not patternsleuth_tool:
        raise RuntimeError('invalid patternsleuth tool entry')
    for entry in patternsleuth_tool.cache_entries:
        if entry.release_tag == tag:
            return entry
    raise RuntimeError(f"Patternsleuth cache entry with tag '{tag}' not found.")


def get_tool_install_dir(tool_name: str) -> str:
    if settings.is_windows():
        platform_name = 'windows'
    # elif settings.is_linux():
    #     platform_name = 'linux'
    else:
        raise RuntimeError('You are on an unsupported os')
    return os.path.normpath(os.path.join(
        cache.get_cache_dir(), "tools", tool_name, platform_name, get_current_patternsleuth_release_tag()
    ))


def get_patternsleuth_directory() -> pathlib.Path | None:
    default_value = get_tool_install_dir("patternsleuth")

    config_value = None
    if settings.settings_information.settings:
        config_value = settings.settings_information.settings.get("patternsleuth_info", {}).get(
            "patternsleuth_dir", None
        )

    env_value = os.environ.get("TEMPO_PATTERNSLEUTH_DIR")

    cli_value = None
    if "--patternsleuth-dir" in sys.argv:
        idx = sys.argv.index("--patternsleuth-dir")
        if idx + 1 < len(sys.argv):
            cli_value = sys.argv[idx + 1]
        else:
            raise RuntimeError("you passed --patternsleuth-dir without a tag after")

    prioritized_value = cli_value or env_value or config_value or default_value

    if not os.path.isabs(prioritized_value):
        return pathlib.Path(str(settings.settings_information.settings_json_dir.path), prioritized_value).resolve()
    else:
        return pathlib.Path(prioritized_value).resolve()


AES_KEY_REGEX = re.compile(r'\b0x[0-9a-fA-F]{64}\b')

def run_patternsleuth_aes_key_scan_command(
    game_exe_path: pathlib.Path | None = None,
    patternsleuth_exe: pathlib.Path | None = None,
) -> list[str]:

    if game_exe_path is None:
        game_exe_path = settings.get_game_exe_path()

    if not game_exe_path:
        raise RuntimeError(
            'There was no game exe path provided, so we cannot run the AES key scan.'
        )

    game_exe_path = pathlib.Path(game_exe_path)

    if patternsleuth_exe is None:
        patternsleuth_exe = pathlib.Path(get_patternsleuth_package_path())

    if not game_exe_path.exists():
        raise FileNotFoundError(f'Game exe not found: {game_exe_path}')

    if not patternsleuth_exe.exists():
        raise FileNotFoundError(f'PatternSleuth not found: {patternsleuth_exe}')

    command: list[str] = [
        str(patternsleuth_exe),
        'scan',
        '--resolver',
        'AESKeys',
        '--path',
        str(game_exe_path),
    ]

    result = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )

    output = f"{result.stdout}\n{result.stderr}"

    seen: set[str] = set()
    keys: list[str] = []
    for key in AES_KEY_REGEX.findall(output):
        if key not in seen:
            seen.add(key)
            keys.append(key)

    return keys


def parse_engine_version(output: str) -> dict | None:
    """
    Extract EngineVersion major/minor from PatternSleuth output.
    Returns:
        {"major": 4, "minor": 27} or None if not found
    """
    match = re.search(r'EngineVersion\((\d+)\.(\d+)\)', output)
    if not match:
        return None

    major, minor = match.groups()
    return {
        "major": int(major),
        "minor": int(minor),
    }


def run_patternsleuth_engine_version_scan_command(
    game_exe_path: pathlib.Path | None = None,
    patternsleuth_exe: pathlib.Path | None = None,
) -> dict | None:

    if game_exe_path is None:
        game_exe_path = settings.get_game_exe_path()

    if not game_exe_path:
        raise RuntimeError(
            'There was no game exe path provided, so we cannot run the AES key scan.'
        )

    game_exe_path = pathlib.Path(game_exe_path)

    if patternsleuth_exe is None:
        patternsleuth_exe = pathlib.Path(get_patternsleuth_package_path())

    if not game_exe_path.exists():
        raise FileNotFoundError(f'Game exe not found: {game_exe_path}')

    if not patternsleuth_exe.exists():
        raise FileNotFoundError(f'PatternSleuth not found: {patternsleuth_exe}')

    command: list[str] = [
        str(patternsleuth_exe),
        'scan',
        '--resolver',
        'EngineVersion',
        '--path',
        str(game_exe_path),
    ]

    result = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )

    output = f"{result.stdout}\n{result.stderr}"
    engine_version = parse_engine_version(output)
    if not engine_version:
        raise RuntimeError('parsing unreal engine version with patternsleuth failed.')
    logger.log_message(f'unreal engine major version: {engine_version["major"]}')
    logger.log_message(f'unreal engine minor version: {engine_version["minor"]}')
    return engine_version


def parse_build_configuration(output: str) -> str | None:
    """
    Extracts the BuildConfiguration value from PatternSleuth table output.
    """
    match = re.search(
        r'^\|\s*BuildConfiguration\s*\|\s*([A-Za-z_]+)\s*\|$',
        output,
        re.MULTILINE,
    )
    if not match:
        return None
    return match.group(1)


def run_patternsleuth_build_configuration_scan_command(
    game_exe_path: pathlib.Path | None = None,
    patternsleuth_exe: pathlib.Path | None = None,
) -> str:

    if game_exe_path is None:
        game_exe_path = settings.get_game_exe_path()

    if not game_exe_path:
        raise RuntimeError(
            'There was no game exe path provided, so we cannot run the build configuration scan.'
        )

    game_exe_path = pathlib.Path(game_exe_path)

    if patternsleuth_exe is None:
        patternsleuth_exe = pathlib.Path(get_patternsleuth_package_path())

    if not game_exe_path.exists():
        raise FileNotFoundError(f'Game exe not found: {game_exe_path}')

    if not patternsleuth_exe.exists():
        raise FileNotFoundError(f'PatternSleuth not found: {patternsleuth_exe}')

    command: list[str] = [
        str(patternsleuth_exe),
        'scan',
        '--resolver',
        'BuildConfiguration',
        '--path',
        str(game_exe_path),
    ]

    result = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )

    output = f"{result.stdout}\n{result.stderr}"
    build_configuration = parse_build_configuration(output)

    if not build_configuration:
        raise RuntimeError(
            f'Parsing build configuration with PatternSleuth failed.\n\nOutput:\n{output}'
        )

    logger.log_message(f'Build Configuration: {build_configuration}')
    return build_configuration
