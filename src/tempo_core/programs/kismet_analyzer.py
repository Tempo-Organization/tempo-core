from pathlib import Path

from tempo_core import settings, data_structures, app_runner


def run_gen_cfg_tree_command(
    kismet_analyzer_executable: Path,
    mappings_file: Path | None,
    asset_tree: Path,
    output_tree: Path,
) -> None:
    project_name = settings.get_uproject_name()
    if not project_name:
        # add other ways of specifying the uproject name in case of not using a personal uproject or other cases alter on
        raise RuntimeError('There was not a valid uproject specified within the config file or other ways')
    exec_mode = data_structures.ExecutionMode.SYNC
    unreal_engine_dir = settings.get_unreal_engine_dir()
    unreal_engine_version_str = settings.get_unreal_engine_version(unreal_engine_dir)
    if not unreal_engine_version_str:
        raise RuntimeError('was unable to obtain the unreal engine version string for run gen cfg tree command from kismet analyzer.')
    kismet_version_str = unreal_engine_version_str.get_kismet_analyzer_unreal_version_str()

    if mappings_file:
        args = [
            'gen-cfg-tree',
            '--version',
            kismet_version_str,
            '--mappings',
            mappings_file,
            asset_tree,
            output_tree,
            project_name,
        ]
    else:
        args = [
            'gen-cfg-tree',
            '--version',
            kismet_version_str,
            asset_tree,
            output_tree,
            project_name,
        ]


    app_runner.run_app(
        exe_path=kismet_analyzer_executable,
        exec_mode=exec_mode,
        args=args,
    )
