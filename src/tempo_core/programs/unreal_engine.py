import json
import os

from tempo_core import file_io, process_management, settings
from tempo_core.data_structures import PackagingDirType, UnrealEngineVersion


def get_game_process_name(input_game_exe_path: str) -> str:
    return process_management.get_process_name(input_game_exe_path)


def get_unreal_engine_version_from_build_version_file(engine_path: str) -> UnrealEngineVersion:
    version_file_path = f"{engine_path}/Engine/Build/Build.version"
    file_io.check_path_exists(version_file_path)
    with open(version_file_path) as f:
        version_info = json.load(f)
        return UnrealEngineVersion( 
            major_version=version_info["MajorVersion"],
            minor_version=version_info["MinorVersion"]
        )


def get_game_paks_dir(uproject_file_path: str, game_dir: str) -> str:
    return os.path.join(
        os.path.dirname(game_dir),
        get_uproject_name(uproject_file_path),
        "Content",
        "Paks"
    )


def get_is_game_iostore(uproject_file_path: str, game_dir: str) -> bool:
    extensions = [".ucas", ".utoc", "ucas", "utoc"]
    _game_dir = game_dir
    _uproject_file_path = uproject_file_path
    is_game_iostore = False
    all_files = file_io.get_files_in_tree(
        get_game_paks_dir(_uproject_file_path, _game_dir)
    )
    for file in all_files:
        file_extensions = file_io.get_file_extensions(file)
        for file_extension in file_extensions:
            if file_extension in extensions:
                is_game_iostore = True
                break
    return is_game_iostore


def get_game_dir(game_exe_path: str):
    return os.path.dirname(os.path.dirname(os.path.dirname(game_exe_path)))


def get_game_content_dir(game_dir: str):
    return os.path.join(game_dir, "Content")


def get_game_pak_folder_archives(uproject_file_path: str, game_dir: str) -> list:
    if get_is_game_iostore(uproject_file_path, game_dir):
        return ["pak", "utoc", "ucas"]
    return ["pak"]


def get_win_dir_type(unreal_engine_dir: str) -> PackagingDirType:
    if is_game_ue5(unreal_engine_dir):
        return PackagingDirType.WINDOWS
    return PackagingDirType.WINDOWS_NO_EDITOR


def get_editor_cmd_path(unreal_engine_dir: str) -> str:
    if settings.is_windows():
        if get_win_dir_type(unreal_engine_dir) == PackagingDirType.WINDOWS_NO_EDITOR:
            engine_path_suffix = "UE4Editor-Cmd.exe"
        else:
            engine_path_suffix = "UnrealEditor-Cmd.exe"
        return f'"{unreal_engine_dir}/Engine/Binaries/Win64/{engine_path_suffix}"'
    else:
        if get_win_dir_type(unreal_engine_dir) == PackagingDirType.WINDOWS_NO_EDITOR:
            engine_path_suffix = "UE4Editor-Cmd"
        else:
            engine_path_suffix = "UnrealEditor-Cmd"
        return f'"{unreal_engine_dir}/Engine/Binaries/Linux/{engine_path_suffix}"'


def is_game_ue5(unreal_engine_dir: str) -> bool:
    return settings.get_unreal_engine_version(unreal_engine_dir).major_version == 5


def is_game_ue4(unreal_engine_dir: str) -> bool:
    return settings.get_unreal_engine_version(unreal_engine_dir).major_version == 4


def get_unreal_editor_exe_path(unreal_engine_dir: str) -> str:
    if settings.is_windows():
        if get_win_dir_type(unreal_engine_dir) == PackagingDirType.WINDOWS_NO_EDITOR:
            engine_path_suffix = "UE4Editor.exe"
        else:
            engine_path_suffix = "UnrealEditor.exe"
        return os.path.join(
            unreal_engine_dir, "Engine", "Binaries", "Win64", engine_path_suffix
        )
    else:
        if get_win_dir_type(unreal_engine_dir) == PackagingDirType.WINDOWS_NO_EDITOR:
            engine_path_suffix = "UE4Editor"
        else:
            engine_path_suffix = "UnrealEditor"
        return os.path.join(
            unreal_engine_dir, "Engine", "Binaries", "Linux", engine_path_suffix
        )


def get_win_dir_str(unreal_engine_dir: str) -> str:
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


def get_cooked_uproject_dir(uproject_file_path: str, unreal_engine_dir: str) -> str:
    uproject_dir = get_uproject_dir(uproject_file_path)
    win_dir_name = get_win_dir_str(unreal_engine_dir)
    uproject_name = get_uproject_name(uproject_file_path)
    return os.path.join(uproject_dir, "Saved", "Cooked", win_dir_name, uproject_name)


def get_uproject_name(uproject_file_path: str) -> str:
    return os.path.splitext(os.path.basename(uproject_file_path))[0]


def get_uproject_dir(uproject_file_path: str) -> str:
    return os.path.dirname(uproject_file_path)


def get_saved_cooked_dir(uproject_file_path: str) -> str:
    uproject_dir = get_uproject_dir(uproject_file_path)
    return os.path.join(uproject_dir, "Saved", "Cooked")


def get_engine_window_title(uproject_file_path: str) -> str:
    return f"{process_management.get_process_name(uproject_file_path)[:-9]} - Unreal Editor"


def get_engine_process_name(unreal_dir: str) -> str:
    return process_management.get_process_name(get_unreal_editor_exe_path(unreal_dir))


def get_build_target_file_path(uproject_file_path: str) -> str:
    uproject_dir = get_uproject_dir(uproject_file_path)
    uproject_name = get_uproject_name(uproject_file_path)
    if settings.is_windows():
        target_platform = "Win64"
    else:
        target_platform = "Linux"
    return os.path.join(uproject_dir, "Binaries", target_platform, f"{uproject_name}.target")


def has_build_target_been_built(uproject_file_path: str) -> bool:
    return os.path.exists(get_build_target_file_path(uproject_file_path))


def get_unreal_pak_exe_path(unreal_engine_dir: str) -> str:
    if settings.is_windows():
            return os.path.join(
                unreal_engine_dir, "Engine", "Binaries", "Win64", "UnrealPak.exe"
            )
    else:
            return os.path.join(
                unreal_engine_dir, "Engine", "Binaries", "Linux", "UnrealPak"
            )


def get_game_window_title(input_game_exe_path: str) -> str:
    return os.path.splitext(get_game_process_name(input_game_exe_path))[0]


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
