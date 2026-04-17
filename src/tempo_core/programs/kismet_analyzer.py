import os
import pathlib

from tempo_core import settings, data_structures, app_runner


def run_gen_cfg_tree_command(
    kismet_analyzer_executable: pathlib.Path,
    mappings_file: pathlib.Path | None,
    asset_tree: pathlib.Path,
    output_tree: pathlib.Path
):
    project_name = settings.get_uproject_name()
    if not project_name:
        # add other ways of specifying the uproject name in case of not using a personal uproject or other cases alter on
        raise RuntimeError('There was not a valid uproject specified within the config file or other ways')
    exe_path = os.path.normpath(str(kismet_analyzer_executable))
    exec_mode = data_structures.ExecutionMode.SYNC
    args = [
        'gen-cfg-tree',
        '--version',
        settings.get_unreal_engine_version(settings.get_unreal_engine_dir()).get_kismet_analyzer_unreal_version_str() # ty: ignore
    ]

    if mappings_file:
        args.extend([
            '--mappings',
            os.path.normpath(str(mappings_file)),
        ])

    args.extend([
        os.path.normpath(str(asset_tree)),
        os.path.normpath(str(output_tree)),
        project_name,
    ])


    app_runner.run_app(
        exe_path=exe_path,
        exec_mode=exec_mode,
        args=args
    )
