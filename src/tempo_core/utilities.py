from tempo_binary_tool_manager.manager import is_windows, is_linux
import os
import shutil
from pathlib import Path

from tempo_core import file_io, settings
from tempo_core.data_structures import CompressionType
from tempo_core.programs import unreal_engine


def get_game_dir() -> Path | None:
    game_exe_path = settings.get_game_exe_path()
    if not game_exe_path:
        return None
    game_dir = game_exe_path.parent.parent.parent
    if not game_dir:
        return None
    return game_dir


def get_game_dir_or_raise() -> Path:
    game_dir = get_game_dir()
    if game_dir:
        return game_dir
    raise NotADirectoryError('Was unable to obtain a game directory.')


def get_game_paks_dir() -> Path:
    game_dir = get_game_dir_or_raise()
    alt_game_dir = game_dir.parent
    potential_alt_dir_name = settings.get_alt_packing_dir_name()
    if potential_alt_dir_name:
        return Path(alt_game_dir / alt_game_dir / "Content" / "Paks")
    uproject_file = settings.get_uproject_file_or_raise()
    return Path(game_dir.parent / unreal_engine.get_uproject_name(uproject_file) / 'Content' / 'Paks')


def get_uproject_dir() -> Path | None:
    uproject_file = settings.get_uproject_file()
    if uproject_file:
        return uproject_file.parent
    return None


def get_uproject_dir_or_raise() -> Path:
    uproject_dir = get_uproject_dir()
    if not uproject_dir:
        raise NotADirectoryError('Was unable to obtain a valid uproject directory.')
    return uproject_dir


def get_uproject_tempo_dir() -> Path | None:
    uproject_dir = get_uproject_dir()
    if uproject_dir:
        return Path(uproject_dir / "Plugins" / "Tempo")
    return None


def get_uproject_tempo_resources_dir() -> Path | None:
    uproject_tempo_dir = get_uproject_tempo_dir()
    if uproject_tempo_dir:
        return Path(uproject_tempo_dir / 'resources')
    return None


def get_use_mod_name_dir_name_override(mod_name: str) -> bool:
    return get_mod_info_from_mod_name(mod_name).get(
        "mod_name_dir_name_override", False,
    )


def get_mod_name_dir_name_override(mod_name: str) -> str:
    return get_mod_info_from_mod_name(mod_name)["mod_name_dir_name_override"]


def get_mod_name_dir_name(mod_name: str) -> str:
    if get_use_mod_name_dir_name_override(mod_name):
        return get_mod_name_dir_name_override(mod_name)
    return mod_name


def get_pak_dir_structure(mod_name: str) -> str:
    mods_info_dict = settings.get_mods_info_dict_from_json()
    dir_to_return = mods_info_dict[mod_name].get("pak_dir_structure", None)
    if dir_to_return:
        return dir_to_return
    pak_dir_structure_missing_error = "Could not find the proper pak dir structure within the mod entry in the provided settings file"
    raise RuntimeError(pak_dir_structure_missing_error)


def get_mod_compression_type(mod_name: str) -> CompressionType:
    mods_info_dict = settings.get_mods_info_dict_from_json()
    compression_type_to_return = mods_info_dict[mod_name].get("compression_type", None)
    if compression_type_to_return:
        return compression_type_to_return
    missing_compression_type_error = (
        f'Could not find the compression type for the following mod name "{mod_name}"'
    )
    raise RuntimeError(missing_compression_type_error)


def get_unreal_mod_tree_type_str(mod_name: str) -> str:
    mods_info_dict = settings.get_mods_info_dict_from_json()
    unreal_mod_tree_type_to_return = mods_info_dict[mod_name].get("mod_name_dir_type", None)
    if unreal_mod_tree_type_to_return:
        return unreal_mod_tree_type_to_return
    missing_mod_tree_type_error = f'Was unable to find the unreal mod tree type for the following mod name "{mod_name}"'
    raise RuntimeError(missing_mod_tree_type_error)


def get_mod_info_from_mod_name(mod_name: str) -> dict:
    mods_info_dict = settings.get_mods_info_dict_from_json()
    mod_info_dict = mods_info_dict.get(mod_name, None)
    if mod_info_dict:
        return mod_info_dict
    missing_mods_info_dict_error = (
        f'Was unable to find the mods info dict for the following mod name "{mod_name}"'
    )
    raise RuntimeError(missing_mods_info_dict_error)


def get_mod_name_dir(mod_name: str) -> Path:
    uproject_file = settings.get_uproject_file()
    if mod_name in settings.settings_information.mod_names and uproject_file:
        uproject_dir = unreal_engine.get_uproject_dir(uproject_file)
        unreal_mod_tree_type = get_unreal_mod_tree_type_str(mod_name)
        return Path(uproject_dir / "Saved" / "Cooked" / unreal_mod_tree_type / mod_name)
    get_mod_name_dir_name_error = "Was unable to find the mod name dir name, or the uproject file (not both)"
    raise RuntimeError(get_mod_name_dir_name_error)


def get_mod_name_dir_files(mod_name: str) -> list[Path]:
    return file_io.get_files_in_tree(get_mod_name_dir(mod_name))


def get_persistent_mod_files(mod_name: str) -> list[Path]:
    return file_io.get_files_in_tree(settings.get_persistent_mod_dir(mod_name))


def clean_temp_dir() -> None:
    temp_dir = settings.get_temp_directory()
    if temp_dir.is_dir():
        shutil.rmtree(temp_dir)


def filter_file_paths(paths_dict: dict[Path, Path]) -> dict[Path, Path]:
    filtered_dict = {}
    path_dict_keys = paths_dict.keys()
    for path_dict_key in path_dict_keys:
        if path_dict_key.is_file():
            filtered_dict[path_dict_key] = paths_dict[path_dict_key]
    return filtered_dict


def get_game_window_title() -> str:
    potential_window_title_override = settings.get_window_title_override()
    if potential_window_title_override:
        return potential_window_title_override
    else:
        game_exe_path = settings.get_game_exe_path()
        if game_exe_path:
            return unreal_engine.get_game_process_name(game_exe_path)
        return 'Unknown'


def get_maximum_command_length() -> int:
    if is_windows():
        return 32767
    elif is_linux():
        return os.sysconf('SC_ARG_MAX') # ty: ignore
    else:
        raise RuntimeError('unsupported os')


def chunk_strings(strings: list[str], max_length: int) -> list[list[str]]:
    result = []
    current_chunk = []
    current_length = 0

    for s in strings:
        if len(s) > max_length:
            raise ValueError(f"String '{s}' exceeds max_length ({max_length})")

        if current_length + len(s) <= max_length:
            current_chunk.append(s)
            current_length += len(s)
        else:
            result.append(current_chunk)
            current_chunk = [s]
            current_length = len(s)

    if current_chunk:
        result.append(current_chunk)

    return result
