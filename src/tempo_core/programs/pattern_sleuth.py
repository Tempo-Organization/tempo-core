import re
from pathlib import Path
import subprocess
import json

from tempo_core import settings, logger, manager, env
from tempo_core.data_structures import UnrealEngineVersion

from tempo_binary_tools import patternsleuth


AES_KEY_REGEX = re.compile(r'\b0x[0-9a-fA-F]{64}\b')

def run_patternsleuth_aes_key_scan_command(
    game_exe_path: Path | None = None,
    patternsleuth_exe: Path | None = None,
) -> list[str]:

    if not game_exe_path:
        game_exe_path = settings.get_game_exe_path_or_raise()

    if not patternsleuth_exe:
        tool_info = patternsleuth.PatternsleuthToolInfo(cache=manager.tools_cache)
        tool_info.ensure_tool_installed()
        patternsleuth_exe = Path(tool_info.get_executable_path())

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


def parse_engine_version(output: str) -> UnrealEngineVersion | None:
    """
    Extract EngineVersion major/minor from PatternSleuth output.
    Returns:
        {"major": 4, "minor": 27} or None if not found
    """
    match = re.search(r'EngineVersion\((\d+)\.(\d+)\)', output)
    if not match:
        return None

    major, minor = match.groups()
    return UnrealEngineVersion(major_version=int(major), minor_version=int(minor))


def run_patternsleuth_engine_version_scan_command(
    game_exe_path: Path | None = None,
    patternsleuth_exe: Path | None = None,
) -> UnrealEngineVersion | None:

    if not game_exe_path:
        game_exe_path = settings.get_game_exe_path_or_raise()

    if not patternsleuth_exe:
        tool_info = patternsleuth.PatternsleuthToolInfo(cache=manager.tools_cache)
        tool_info.ensure_tool_installed()
        patternsleuth_exe = Path(tool_info.get_executable_path())

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
    logger.log_message(f'output: {output}')
    unreal_engine_version = parse_engine_version(output)
    if not unreal_engine_version:
        raise RuntimeWarning('parsing unreal engine version with patternsleuth failed.')
    logger.log_message(f'unreal engine major version: {unreal_engine_version.major_version}')
    logger.log_message(f'unreal engine minor version: {unreal_engine_version.minor_version}')
    return unreal_engine_version


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
    game_exe_path: Path | None = None,
    patternsleuth_exe: Path | None = None,
) -> str:

    if not game_exe_path:
        game_exe_path = settings.get_game_exe_path_or_raise()

    if not patternsleuth_exe:
        tool_info = patternsleuth.PatternsleuthToolInfo(cache=manager.tools_cache)
        tool_info.ensure_tool_installed()
        patternsleuth_exe = Path(tool_info.get_executable_path())

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
            f'Parsing build configuration with PatternSleuth failed.\n\nOutput:\n{output}',
        )

    logger.log_message(f'Build Configuration: {build_configuration}')
    return build_configuration


def dump_engine_version(config_file: Path, directory: Path, dump_to_tempo_config: bool) -> UnrealEngineVersion | None:

    unreal_engine_version = run_patternsleuth_engine_version_scan_command()
    if not unreal_engine_version:
        raise RuntimeError("was unable to obtain the unreal engine version with patternsleuth")

    directory.mkdir(parents=True, exist_ok=True)

    output_path = Path(directory / "engine_version.json")

    data = {
        "engine_major_version": unreal_engine_version.major_version,
        "engine_minor_version": unreal_engine_version.minor_version,
    }

    with Path.open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

    logger.log_message(f'output path: {output_path}')

    env_var = os.getenv('TEMPO_DUMP_PATTERNSLEUTH_VERSION')

    if not dump_to_tempo_config or not env.env_true(env_var):
        return unreal_engine_version

    with Path.open(config_file, "r", encoding="utf-8") as f:
        settings = json.load(f)

    engine_info = settings.setdefault("engine_info", {})

    engine_info["unreal_engine_major_version"] = unreal_engine_version.major_version
    engine_info["unreal_engine_minor_version"] = unreal_engine_version.minor_version

    with Path.open(config_file, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=4)

    logger.log_message(f"updated settings json: {config_file}")

    return unreal_engine_version
