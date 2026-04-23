import os
from pathlib import Path

from tempo_core import settings, app_runner, data_structures


def run_dump_jmap_jmap_command(
    jmap_executable: Path,
    game_pid: int,
    output_jmap_location: Path,
) -> None:
    unreal_engine_dir = settings.get_unreal_engine_dir()
    if not unreal_engine_dir:
        raise RuntimeError('no unreal engine dir')
    unreal_engine_version = settings.get_unreal_engine_version(unreal_engine_dir)
    if not unreal_engine_version:
        raise RuntimeError('no unreal engine version')
    engine_ver_string = unreal_engine_version.get_jmap_unreal_version_str()
    os.environ["PATTERNSLEUTH_RES_EngineVersion"] = engine_ver_string
    exec_mode = data_structures.ExecutionMode.SYNC
    args = [
        '--pid',
        game_pid,
        output_jmap_location,
    ]

    app_runner.run_app(
        exe_path=jmap_executable,
        exec_mode=exec_mode,
        args=args, # ty: ignore
    )
