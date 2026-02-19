import os
import sys
import pathlib
import requests

from tempo_core import settings, cache, logger, app_runner, data_structures, utilities


def get_jmap_package_path():
    return os.path.normpath(f'{str(get_jmap_directory())}/{get_executable_name()}')


def get_current_jmap_release_tag() -> str:

    default_value = "latest"
    config_value = None

    if settings.settings_information.settings:
        config_value = settings.settings_information.settings.get('jmap_info', {}).get('jmap_release_tag')

    env_value = os.environ.get('TEMPO_JMAP_RELEASE_TAG')

    cli_value = None
    if '--jmap-release-tag' in sys.argv:
        idx = sys.argv.index('--jmap-release-tag')
        if idx + 1 < len(sys.argv):
            cli_value = sys.argv[idx + 1]
        else:
            raise RuntimeError('You passed --jmap-release-tag without a tag after it.')

    prioritized_value = cli_value or env_value or config_value or default_value

    if prioritized_value == "latest":
        try:
            response = requests.get("https://api.github.com/repos/trumank/jmap/releases/latest", timeout=5)
            response.raise_for_status()
            return response.json().get("tag_name", "latest")
        except Exception as e:
            logger.log_message(f"[Warning] Failed to fetch latest Jmap release tag from GitHub: {e}")
            return "latest"

    return prioritized_value


def get_executable_name() -> str:
    if settings.is_windows():
        return 'jmap_dumper.exe'
    elif settings.is_linux():
        return 'jmap_dumper'
    else:
        raise ValueError('unsupported os')


def get_file_to_download() -> str:
    if settings.is_windows():
        return 'jmap_dumper-x86_64-pc-windows-msvc.zip'
    elif settings.is_linux():
        return 'jmap_dumper-x86_64-unknown-linux-gnu.tar.xz'
    else:
        raise ValueError('unsupported os')


def get_download_url() -> str:
    base_url_prefix = f'https://github.com/trumank/jmap/releases/download/{get_current_jmap_release_tag()}/jmap_dumper-x86_64-'
    if settings.is_windows():
        return f'{base_url_prefix}pc-windows-msvc.zip'
    elif settings.is_linux():
        return f'{base_url_prefix}unknown-linux-gnu.tar.xz'
    else:
        raise ValueError('unsupported os')


def install_tool_jmap():
    cache.install_tool_to_cache(
        tools = cache.TempoCache,
        tool_name = 'jmap',
        version_tag = get_current_jmap_release_tag(),
        file_paths = [],
        executable_path = get_executable_name(),
        file_to_download = get_file_to_download(),
        download_url = get_download_url()
    )


def is_current_preferred_jmap_version_installed() -> bool:
    # this doesn't check the tag like it should
    # Check if the jmap tool is present in the cache and has a valid version
    for tool in cache.TempoCache.tool_entries:
        if tool.get_repo_name().lower() == "jmap":
            for entry in tool.cache_entries:
                if entry.is_cache_valid():
                    return True
    return False


def get_jmap_tool_entry() -> cache.Tool | None:
    # Return the Jmap tool entry if present
    for tool in cache.TempoCache.tool_entries:
        if tool.get_repo_name().lower() == "jmap":
            return tool
    logger.log_message("Jmap tool not found in cache. Please install it first.")
    return None


def get_jmap_cache_entry_by_tag(tag: str) -> cache.CacheEntry:
    jmap_tool = get_jmap_tool_entry()
    if not jmap_tool:
        raise RuntimeError('invalid jmap tool entry')
    for entry in jmap_tool.cache_entries:
        if entry.release_tag == tag:
            return entry
    raise RuntimeError(f"Jmap cache entry with tag '{tag}' not found.")


def get_tool_install_dir(tool_name: str) -> str:
    if settings.is_windows():
        platform_name = 'windows'
    elif settings.is_linux():
        platform_name = 'linux'
    else:
        raise RuntimeError('You are on an unsupported os')
    return os.path.normpath(os.path.join(
        cache.get_cache_dir(), "tools", tool_name, platform_name, get_current_jmap_release_tag()
    ))


def get_jmap_directory() -> pathlib.Path | None:
    default_value = get_tool_install_dir("jmap")

    config_value = None
    if settings.settings_information.settings:
        config_value = settings.settings_information.settings.get("jmap_info", {}).get(
            "jmap_dir", None
        )

    env_value = os.environ.get("TEMPO_JMAP_DIR")

    cli_value = None
    if "--jmap-dir" in sys.argv:
        idx = sys.argv.index("--jmap-dir")
        if idx + 1 < len(sys.argv):
            cli_value = sys.argv[idx + 1]
        else:
            raise RuntimeError("you passed --jmap-dir without a tag after")

    prioritized_value = cli_value or env_value or config_value or default_value

    if not os.path.isabs(prioritized_value):
        return pathlib.Path(str(settings.settings_information.settings_json_dir.path), prioritized_value).resolve()
    else:
        return pathlib.Path(prioritized_value).resolve()


# def run_dump_jmap_jmap_command(
#     jmap_executable: str,
#     game_pid: int,
#     output_jmap_location: pathlib.Path
# ):
#     engine_ver_string = settings.get_unreal_engine_version(settings.get_unreal_engine_dir()).get_jmap_unreal_version_str()
#     os.environ["PATTERNSLEUTH_RES_EngineVersion"] = engine_ver_string
#     import subprocess
#     exe_path = os.path.normpath(str(jmap_executable))

#     cmd = [
#         exe_path,
#         '--pid',
#         str(game_pid),
#         str(output_jmap_location)
#     ]

#     subprocess.run(
#         cmd,
#         check=True
#     )


def run_dump_jmap_jmap_command(
    jmap_executable: str,
    game_pid: int,
    output_jmap_location: pathlib.Path
):
    engine_ver_string = settings.get_unreal_engine_version(settings.get_unreal_engine_dir()).get_jmap_unreal_version_str()
    os.environ["PATTERNSLEUTH_RES_EngineVersion"] = engine_ver_string
    exe_path = os.path.normpath(str(jmap_executable))
    exec_mode = data_structures.ExecutionMode.SYNC
    args = [
        '--pid',
        game_pid,
        output_jmap_location
    ]

    app_runner.run_app(
        exe_path=exe_path,
        exec_mode=exec_mode,
        args=args
    )
