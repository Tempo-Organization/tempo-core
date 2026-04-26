import re
from pathlib import Path
import subprocess

from tempo_core import settings, logger, manager

from tempo_binary_tools import patternsleuth


AES_KEY_REGEX = re.compile(r'\b0x[0-9a-fA-F]{64}\b')

def run_patternsleuth_aes_key_scan_command(
    game_exe_path: Path | None = None,
    patternsleuth_exe: Path | None = None,
) -> list[str]:

    if game_exe_path is None:
        game_exe_path = settings.get_game_exe_path()

    if not game_exe_path:
        raise RuntimeError(
            'There was no game exe path provided, so we cannot run the AES key scan.',
        )

    game_exe_path = Path(game_exe_path)

    if patternsleuth_exe is None:
        tool_info = patternsleuth.PatternsleuthToolInfo(cache=manager.tools_cache)
        tool_info.ensure_tool_installed()
        patternsleuth_exe = Path(tool_info.get_executable_path())

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


def parse_engine_version(output: str) -> dict[str, int] | None:
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
    game_exe_path: Path | None = None,
    patternsleuth_exe: Path | None = None,
) -> dict | None:

    if game_exe_path is None:
        game_exe_path = settings.get_game_exe_path()

    if not game_exe_path:
        raise RuntimeError(
            'There was no game exe path provided, so we cannot run the AES key scan.',
        )

    game_exe_path = Path(game_exe_path)

    if patternsleuth_exe is None:
        tool_info = patternsleuth.PatternsleuthToolInfo(cache=manager.tools_cache)
        tool_info.ensure_tool_installed()
        patternsleuth_exe = Path(tool_info.get_executable_path())

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
    game_exe_path: Path | None = None,
    patternsleuth_exe: Path | None = None,
) -> str:

    if game_exe_path is None:
        game_exe_path = settings.get_game_exe_path()

    if not game_exe_path:
        raise RuntimeError(
            'There was no game exe path provided, so we cannot run the build configuration scan.',
        )

    game_exe_path = Path(game_exe_path)

    if patternsleuth_exe is None:
        tool_info = patternsleuth.PatternsleuthToolInfo(cache=manager.tools_cache)
        tool_info.ensure_tool_installed()
        patternsleuth_exe = Path(tool_info.get_executable_path())

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
            f'Parsing build configuration with PatternSleuth failed.\n\nOutput:\n{output}',
        )

    logger.log_message(f'Build Configuration: {build_configuration}')
    return build_configuration
