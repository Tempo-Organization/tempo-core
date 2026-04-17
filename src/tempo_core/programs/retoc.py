import os
import shutil
import pathlib
import subprocess

from tempo_core.programs import unreal_pak
from tempo_core import settings, data_structures, utilities, logger, app_runner

from tempo_cache_tools import retoc


def run_retoc_to_zen_command(
    input_directory: pathlib.Path,
    output_utoc: pathlib.Path,
    unreal_version: data_structures.UnrealEngineVersion,
) -> list[pathlib.Path]:
    if not pathlib.Path.is_dir(input_directory):
        raise NotADirectoryError(f'Input directory "{input_directory}" does not exist.')

    logger.log_message(unreal_version.get_retoc_unreal_version_str())

    command = [
        retoc.RetocToolInfo().get_executable_path(),
        "to-zen",
        input_directory,
        output_utoc,
        "--version",
        unreal_version.get_retoc_unreal_version_str(),
    ]
    subprocess.run(command)

    output_pak = pathlib.Path(f"{os.path.splitext(output_utoc)[0]}.pak")
    output_ucas = pathlib.Path(f"{os.path.splitext(output_utoc)[0]}.ucas")
    file_paths = [output_pak, output_ucas, pathlib.Path(output_utoc)]

    missing_files = [f for f in file_paths if not f.exists()]
    if missing_files:
        raise FileNotFoundError(f"Missing output files: {missing_files}")

    return file_paths


def make_retoc_mod(mod_name: str, dest_pak_file: str, *, use_symlinks: bool):
    from tempo_core import packing

    old_ucas = pathlib.Path(f"{os.path.splitext(dest_pak_file)[0]}.ucas")
    old_utoc = pathlib.Path(f"{os.path.splitext(dest_pak_file)[0]}.utoc")
    old_file_paths = [old_utoc, old_ucas, pathlib.Path(dest_pak_file)]

    for file in old_file_paths:
        if pathlib.Path.is_file(file):
            pathlib.Path.unlink(file)

    original_mod_dir = unreal_pak.get_pak_dir_to_pack(mod_name)
    original_mod_base_dir = os.path.dirname(original_mod_dir)
    ucas_mod_dir = os.path.normpath(f"{original_mod_base_dir}/{mod_name}_ucas")

    os.makedirs(ucas_mod_dir, exist_ok=True)

    ucas_extensions = {
        ".umap",
        ".uexp",
        ".uptnl",
        ".ubulk",
        ".uasset",
        ".ushaderbytecode",
    }

    for root, _, files in os.walk(original_mod_dir):
        for file in files:
            source_path = os.path.join(root, file)
            rel_path = os.path.relpath(source_path, original_mod_dir)
            ext = os.path.splitext(file)[1].lower()

            if ext in ucas_extensions:
                target_path = os.path.join(ucas_mod_dir, rel_path)
                os.makedirs(os.path.dirname(target_path), exist_ok=True)
                shutil.move(source_path, target_path)

    if any(files for _, _, files in os.walk(ucas_mod_dir)):
        run_retoc_to_zen_command(
            input_directory=pathlib.Path(ucas_mod_dir),
            output_utoc=pathlib.Path(f"{os.path.splitext(dest_pak_file)[0]}.utoc"),
            unreal_version=settings.get_unreal_engine_version(str(settings.get_unreal_engine_dir())), # ty: ignore
        )

    if any(files for _, _, files in os.walk(original_mod_dir)):
        packing.make_pak_repak(mod_name=mod_name, use_symlinks=use_symlinks)

    packing.install_mod_sig(mod_name=mod_name, use_symlinks=use_symlinks)


def install_retoc_mod(*, mod_name: str, use_symlinks: bool):
    # installs packing tool if need be,
    # moves files from various locations over to temp packaging location,
    # makes dirs as need be,
    # makes mod in intermediate location,
    # copies or symlinks files over to final location

    unreal_pak.move_files_for_packing(mod_name)
    intermediate_dest_dir = (
        f"{settings.get_temp_directory()}/{utilities.get_pak_dir_structure(mod_name)}"
    )
    final_dest_dir = os.path.normpath(
        f"{utilities.custom_get_game_paks_dir()}/{utilities.get_pak_dir_structure(mod_name)}"
    )
    extensions = data_structures.unreal_iostore_no_sigs_archive_extensions

    dest_prefix = f"{final_dest_dir}/{mod_name}."
    output_mod_prefix = f"{intermediate_dest_dir}/{mod_name}."
    os.makedirs(intermediate_dest_dir, exist_ok=True)
    os.makedirs(
        f"{utilities.custom_get_game_paks_dir()}/{utilities.get_pak_dir_structure(mod_name)}",
        exist_ok=True,
    )

    for extension in extensions:
        output_file = os.path.normpath(f"{output_mod_prefix}{extension}")
        if os.path.isfile(output_file):
            os.remove(output_file)
        if os.path.islink(output_file):
            os.unlink(output_file)

    make_retoc_mod(
        mod_name, os.path.normpath(f"{output_mod_prefix}pak"), use_symlinks=use_symlinks
    )

    for extension in extensions:
        dest_file = os.path.normpath(f"{dest_prefix}{extension}")
        output_file = os.path.normpath(f"{output_mod_prefix}{extension}")

        if use_symlinks:
            os.symlink(output_file, dest_file)
        else:
            shutil.copy(output_file, dest_file)


def run_gen_script_objects_retoc_command(
    retoc_executable: pathlib.Path,
    jmap_file: pathlib.Path,
    output: pathlib.Path
):
    exe_path = os.path.normpath(str(retoc_executable))
    exec_mode = data_structures.ExecutionMode.SYNC
    args = [
        "gen-script-objects",
        "--version",
        settings.get_unreal_engine_version(settings.get_unreal_engine_dir()).get_retoc_unreal_version_str(), # ty: ignore
        os.path.normpath(jmap_file),
        os.path.normpath(output)
    ]

    app_runner.run_app(
        exe_path=exe_path,
        exec_mode=exec_mode,
        args=args
    )
