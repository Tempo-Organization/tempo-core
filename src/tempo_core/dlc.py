from pathlib import Path

from tempo_core import settings, main_logic
from tempo_core.app_runner import run_app
from tempo_core.programs import unreal_engine


# make function to grab args for each
# make function to grab main command for each
# test if cooking speedups are applicable
# test if other ways to speed this up, or mimic process self but faster
# compression options


def make_base_release(release_version: str, archive_dir: Path) -> None:
    uproject_file = settings.get_uproject_file_or_raise()

    args = [
        "BuildCookRun",
        f'-project="{uproject_file}"',
        "-build",
        "-cook",
        "-stage",
        "-package",
        "-pak",
        f"-createreleaseversion={release_version}",
        "-archive",
        f'-archivedirectory="{str(archive_dir)}"',
    ]
    run_app(
        exe_path=unreal_engine.get_run_uat_script_path(), args=args,
    )


def build_dlc_plugin(plugin_name: str, release_version: str) -> None:
    uproject_file = settings.get_uproject_file_or_raise()

    archive_dir = Path(uproject_file.parent / "Packages/BaseRelease")

    args = [
        "BuildCookRun",
        f'-project="{uproject_file}"',
        "-build",
        "-cook",
        "-stage",
        "-package",
        "-pak",
        f"-DLCName={plugin_name}",
        "-DLCPakPluginFile",
        f"-basedonreleaseversion={release_version}",
        "-archive",
        f'-archivedirectory="{str(archive_dir)}"',
    ]
    run_app(
        exe_path=unreal_engine.get_run_uat_script_path(), args=args,
    )


def generate_dlc_plugin(
    plugin_name: str,
    plugins_directory: Path,
    unreal_engine_major_version: int,
    unreal_engine_minor_version: int,
    is_installed: bool,
    is_hidden: bool,
    category: str,
    created_by: str,
    created_by_url: str,
    description: str,
    docs_url: str,
    editor_custom_virtual_path: str,
    support_url: str,
    version: float,
    version_name: str,
) -> None:
    plugins_directory.mkdir(exist_ok=True, parents=True)

    main_logic.generate_uplugin(
        plugins_directory=plugins_directory,
        plugin_name=plugin_name,
        can_contain_content=True,
        enabled_by_default=True,
        no_code=True,
        is_installed=is_installed,
        is_hidden=is_hidden,
        category=category,
        created_by=created_by,
        created_by_url=created_by_url,
        description=description,
        docs_url=docs_url,
        editor_custom_virtual_path=editor_custom_virtual_path,
        support_url=support_url,
        version=version,
        version_name=version_name,
        engine_major_version=unreal_engine_major_version,
        engine_minor_version=unreal_engine_minor_version,
    )
