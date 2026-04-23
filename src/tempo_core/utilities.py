import os
import shutil
from pathlib import Path

from tempo_core import file_io, settings
from tempo_core.data_structures import CompressionType
from tempo_core.programs import unreal_engine


def custom_get_game_dir() -> Path | None:
    game_exe_path = settings.get_game_exe_path()
    if not game_exe_path:
        return None
    game_dir = unreal_engine.get_game_dir(game_exe_path)
    if not game_dir:
        return None
    return game_dir


def custom_get_game_paks_dir() -> Path:
    game_dir = custom_get_game_dir()
    if not game_dir:
        raise NotADirectoryError('Could not get a valid game dir from custom_game_get_dir')
    alt_game_dir = game_dir.parent
    potential_alt_dir_name = settings.get_alt_packing_dir_name()
    if potential_alt_dir_name:
        return Path(alt_game_dir / alt_game_dir / "Content" / "Paks")
    uproject_file = settings.get_uproject_file()
    if not uproject_file:
        raise FileNotFoundError('Was unable to find a valid uproject file, in custom_get_game_paks_dir')
    return unreal_engine.get_game_paks_dir(uproject_file, game_dir)


def get_uproject_dir() -> Path | None:
    uproject_file = settings.get_uproject_file()
    if uproject_file:
        return uproject_file.parent
    return None


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
    return get_mods_info_dict_from_mod_name(mod_name).get(
        "use_mod_name_dir_name_override", False,
    )


def get_mod_name_dir_name_override(mod_name: str) -> str:
    return get_mods_info_dict_from_mod_name(mod_name)["mod_name_dir_name_override"]


def get_mod_name_dir_name(mod_name: str) -> str:
    if get_use_mod_name_dir_name_override(mod_name):
        return get_mod_name_dir_name_override(mod_name)
    return mod_name


def get_pak_dir_structure(mod_name: str) -> str:
    mods_info_dict = settings.get_mods_info_dict_from_json()
    for mod_key in mods_info_dict.keys():
        if mod_key == mod_name:
            return mods_info_dict[mod_key]["pak_dir_structure"]
    pak_dir_structure_missing_error = "Could not find the proper pak dir structure within the mod entry in the provided settings file"
    raise RuntimeError(pak_dir_structure_missing_error)


def get_mod_compression_type(mod_name: str) -> CompressionType:
    mods_info_dict = settings.get_mods_info_dict_from_json()
    for mod_key in mods_info_dict.keys():
        if mod_key == mod_name:
            return mods_info_dict[mod_key]["compression_type"]
    missing_compression_type_error = (
        f'Could not find the compression type for the following mod name "{mod_name}"'
    )
    raise RuntimeError(missing_compression_type_error)


def get_unreal_mod_tree_type_str(mod_name: str) -> str:
    mods_info_dict = settings.get_mods_info_dict_from_json()
    for mod_key in mods_info_dict.keys():
        if mod_key == mod_name:
            return mods_info_dict[mod_key]["mod_name_dir_type"]
    missing_mod_tree_type_error = f'Was unable to find the unreal mod tree type for the following mod name "{mod_name}"'
    raise RuntimeError(missing_mod_tree_type_error)


def get_mods_info_dict_from_mod_name(mod_name: str) -> dict:
    mods_info_dict = settings.get_mods_info_dict_from_json()
    for mod_key in mods_info_dict.keys():
        if mod_key == mod_name:
            return dict(mods_info_dict[mod_key])
    missing_mods_info_dict_error = (
        f'Was unable to find the mods info dict for the following mod name "{mod_name}"'
    )
    raise RuntimeError(missing_mods_info_dict_error)


def is_mod_name_in_list(mod_name: str) -> bool:
    return any(
        mod_key == mod_name for mod_key in settings.get_mods_info_dict_from_json().keys()
    )


def get_mod_name_dir(mod_name: str) -> Path:
    uproject_file = settings.get_uproject_file()
    if is_mod_name_in_list(mod_name) and uproject_file:
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
