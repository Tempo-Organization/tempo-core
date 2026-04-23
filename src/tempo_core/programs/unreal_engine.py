import os
import json
from pathlib import Path

from tempo_core import file_io, process_management, settings, data_structures
from tempo_core.data_structures import PackagingDirType, UnrealEngineVersion, unreal_engine_build_targets


def get_game_process_name(input_game_exe_path: Path) -> str:
    return process_management.get_process_name(input_game_exe_path)


def get_unreal_engine_version_from_build_version_file(
    engine_path: Path | None,
) -> UnrealEngineVersion | None:
    if not engine_path:
        return None
    version_file_path = Path(engine_path / 'Engine/Build/Build.version')
    if not version_file_path.is_file():
        return None
    with version_file_path.open() as f:
        version_info = json.load(f)
        return UnrealEngineVersion(
            major_version=version_info["MajorVersion"],
            minor_version=version_info["MinorVersion"],
        )


def get_game_paks_dir(uproject_file_path: Path, game_dir: Path) -> Path:
    return Path(game_dir.parent / get_uproject_name(uproject_file_path) / 'Content' / 'Paks')


def get_is_game_iostore(uproject_file_path: Path, game_dir: Path) -> bool:
    first_check = settings.get_is_game_iostore_from_config()
    if first_check:
        return first_check
    extensions = ["ucas", "utoc"]
    _game_dir = game_dir
    _uproject_file_path = uproject_file_path
    is_game_iostore = False
    all_files = file_io.get_files_in_tree(
        get_game_paks_dir(_uproject_file_path, _game_dir),
    )
    for file in all_files:
        file_extensions = file_io.get_file_extensions(str(file))
        for file_extension in file_extensions:
            if file_extension in extensions:
                is_game_iostore = True
                break
    return is_game_iostore


def get_game_dir(game_exe_path: Path) -> Path:
    return game_exe_path.parent.parent.parent


def get_game_content_dir(game_dir: Path) -> Path:
    return Path(game_dir / "Content")


def get_game_pak_folder_archives(uproject_file_path: Path, game_dir: Path) -> list[str]:
    if get_is_game_iostore(uproject_file_path, game_dir):
        return data_structures.unreal_iostore_no_sigs_archive_extensions
    return data_structures.unreal_non_iostore_no_sigs_archive_extensions


def get_win_dir_type(unreal_engine_dir: Path) -> PackagingDirType:
    if is_game_ue5(unreal_engine_dir):
        return PackagingDirType.WINDOWS
    return PackagingDirType.WINDOWS_NO_EDITOR


def get_editor_cmd_path(unreal_engine_dir: Path) -> Path:
    if settings.is_windows():
        if get_win_dir_type(unreal_engine_dir) == PackagingDirType.WINDOWS_NO_EDITOR:
            engine_path_suffix = "UE4Editor-Cmd.exe"
        else:
            engine_path_suffix = "UnrealEditor-Cmd.exe"
        return Path(unreal_engine_dir / 'Engine/Binaries/Win64' / engine_path_suffix)
    else:
        if get_win_dir_type(unreal_engine_dir) == PackagingDirType.WINDOWS_NO_EDITOR:
            engine_path_suffix = "UE4Editor-Cmd"
        else:
            engine_path_suffix = "UnrealEditor-Cmd"
        return Path(unreal_engine_dir / 'Engine/Binaries/Linux' / engine_path_suffix)


def is_game_ue5(unreal_engine_dir: Path | None) -> bool:
    ue_version = settings.get_unreal_engine_version(unreal_engine_dir)
    if not ue_version:
        raise RuntimeError('No unreal version found, with is game ue5 check')
    return ue_version.major_version == 5


def is_game_ue4(unreal_engine_dir: Path | None) -> bool:
    ue_version = settings.get_unreal_engine_version(unreal_engine_dir)
    if not ue_version:
        raise RuntimeError('No unreal version found, with is game ue4 check')
    return ue_version.major_version == 4


def get_unreal_editor_exe_path(unreal_engine_dir: Path) -> Path:
    if settings.is_windows():
        if get_win_dir_type(unreal_engine_dir) == PackagingDirType.WINDOWS_NO_EDITOR:
            engine_path_suffix = "UE4Editor.exe"
        else:
            engine_path_suffix = "UnrealEditor.exe"
        return Path(unreal_engine_dir / "Engine" / "Binaries" / "Win64" / engine_path_suffix)
    else:
        if get_win_dir_type(unreal_engine_dir) == PackagingDirType.WINDOWS_NO_EDITOR:
            engine_path_suffix = "UE4Editor"
        else:
            engine_path_suffix = "UnrealEditor"
        return Path(unreal_engine_dir / "Engine" / "Binaries" / 'Linux' / engine_path_suffix)


def get_win_dir_str(unreal_engine_dir: Path | None) -> str:
    if settings.is_windows():
        win_dir_type = "Windows"
        if is_game_ue4(unreal_engine_dir):
            win_dir_type = f"{win_dir_type}NoEditor"
        return win_dir_type
    else:
        win_dir_type = "Linux"
        if is_game_ue4(unreal_engine_dir):
            win_dir_type = f"{win_dir_type}NoEditor"
        return win_dir_type


def get_cooked_uproject_dir(uproject_file_path: Path, unreal_engine_dir: Path) -> Path:
    uproject_dir = get_uproject_dir(uproject_file_path)
    win_dir_name = get_win_dir_str(unreal_engine_dir)
    uproject_name = get_uproject_name(uproject_file_path)
    cooked_dir = Path(uproject_dir / 'Saved/Cooked' / win_dir_name / uproject_name)
    return cooked_dir


def get_uproject_name(uproject_file_path: Path) -> str:
    return uproject_file_path.stem


def get_uproject_dir(uproject_file_path: Path) -> Path:
    return uproject_file_path.parent


def get_saved_cooked_dir(uproject_file_path: Path) -> Path:
    uproject_dir = get_uproject_dir(uproject_file_path)
    return Path(uproject_dir / "Saved" / "Cooked")


def get_engine_window_title(uproject_file_path: Path) -> str:
    return f"{process_management.get_process_name(uproject_file_path)[:-9]} - Unreal Editor"


def get_engine_process_name(unreal_dir: Path) -> str:
    return process_management.get_process_name(get_unreal_editor_exe_path(unreal_dir))


def get_build_target_file_path(uproject_file_path: Path) -> Path:
    build_target = settings.get_build_configuration_state()
    if build_target not in unreal_engine_build_targets:
        unsupported_build_configuration_error_message = f'Unsupported build configuration chosen "{build_target}"'
        raise RuntimeError(unsupported_build_configuration_error_message)
    uproject_dir = get_uproject_dir(uproject_file_path)
    uproject_name = get_uproject_name(uproject_file_path)
    target_platform = settings.get_target_platform()
    if build_target == "Development":
        return Path(f'{uproject_dir}/Binaries/{target_platform}/{uproject_name}.target')
    else:
        return Path(f'{uproject_dir}/Binaries/{target_platform}/{uproject_name}-{target_platform}-{build_target}.target')


def has_build_target_been_built(uproject_file_path: Path) -> bool:
    return get_build_target_file_path(uproject_file_path).exists()


def get_unreal_pak_exe_path(unreal_engine_dir: Path) -> Path:
    if settings.is_windows():
        return Path(unreal_engine_dir / "Engine" / "Binaries" / "Win64" / "UnrealPak.exe")
    else:
        return Path(unreal_engine_dir / "Engine" / "Binaries" / "Linux" / "UnrealPak")


def get_game_window_title(input_game_exe_path: Path) -> str:
    return Path(get_game_process_name(input_game_exe_path)).stem


def get_new_uproject_json_contents(
    file_version: int = 3,
    engine_major_association: int = 4,
    engine_minor_association: int = 27,
    category: str = "Modding",
    description: str = "Uproject for modding, generated with tempo.",
) -> str:
    return f'''{{
  "FileVersion": "{file_version}",
  "EngineAssociation": "{engine_major_association}.{engine_minor_association}",
  "Category": "{category}",
  "Description": "{description}"
}}'''
