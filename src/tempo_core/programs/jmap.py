import os
import pathlib

from tempo_core import settings, app_runner, data_structures


def run_dump_jmap_jmap_command(
    jmap_executable: str,
    game_pid: int,
    output_jmap_location: pathlib.Path
):
    unreal_engine_dir = settings.get_unreal_engine_dir()
    if not unreal_engine_dir:
        raise RuntimeError('no unreal engine dir')
    unreal_engine_dir = str(unreal_engine_dir)
    unreal_engine_version = settings.get_unreal_engine_version(unreal_engine_dir)
    if not unreal_engine_version:
        raise RuntimeError('no unreal engine version')
    engine_ver_string = unreal_engine_version.get_jmap_unreal_version_str()
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
        args=args # ty: ignore
    )
