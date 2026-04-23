import os
import shutil
from pathlib import Path
import subprocess

from tempo_core.programs import unreal_pak
from tempo_core import settings, data_structures, utilities, logger, app_runner

from tempo_cache_tools import retoc


def run_retoc_to_zen_command(
    input_directory: Path,
    output_utoc: Path,
    unreal_version: data_structures.UnrealEngineVersion,
) -> list[Path]:
    if not input_directory.is_dir():
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

    output_pak = output_utoc.with_suffix(".pak")
    output_ucas = output_utoc.with_suffix(".ucas")
    file_paths = [output_pak, output_ucas, Path(output_utoc)]

    missing_files = [f for f in file_paths if not f.exists()]
    if missing_files:
        raise FileNotFoundError(f"Missing output files: {missing_files}")

    return file_paths


def make_retoc_mod(mod_name: str, dest_pak_file: Path, *, use_symlinks: bool) -> None:
    from tempo_core import packing
    old_ucas = dest_pak_file.with_suffix(".ucas")
    old_utoc = dest_pak_file.with_suffix(".utoc")
    old_file_paths = [old_utoc, old_ucas, dest_pak_file]

    for file in old_file_paths:
        if file.is_file():
            file.unlink()

    original_mod_dir = unreal_pak.get_pak_dir_to_pack(mod_name)
    original_mod_base_dir = original_mod_dir.parent
    ucas_mod_dir = original_mod_base_dir / f"{mod_name}_ucas"

    ucas_mod_dir.mkdir(parents=True, exist_ok=True)

    ucas_extensions = {
        ".umap",
        ".uexp",
        ".uptnl",
        ".ubulk",
        ".uasset",
        ".ushaderbytecode",
    }

    for root, _, files in original_mod_dir.walk():
        for file in files:
            source_path = Path(root / file)
            rel_path = os.path.relpath(source_path, original_mod_dir)
            ext = Path(file).suffix

            if ext in ucas_extensions:
                target_path = Path(ucas_mod_dir / rel_path)
                target_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(source_path, target_path)

    if any(files for _, _, files in ucas_mod_dir.walk()):
        run_retoc_to_zen_command(
            input_directory=ucas_mod_dir,
            output_utoc=old_utoc,
            unreal_version=settings.get_unreal_engine_version(settings.get_unreal_engine_dir()), # ty: ignore
        )

    if any(files for _, _, files in original_mod_dir.walk()):
        packing.make_pak_repak(mod_name=mod_name, use_symlinks=use_symlinks)

    packing.install_mod_sig(mod_name=mod_name, use_symlinks=use_symlinks)


def install_retoc_mod(*, mod_name: str, use_symlinks: bool) -> None:
    # installs packing tool if need be,
    # moves files from various locations over to temp packaging location,
    # makes dirs as need be,
    # makes mod in intermediate location,
    # copies or symlinks files over to final location

    unreal_pak.move_files_for_packing(mod_name)
    intermediate_dest_dir = Path(settings.get_temp_directory()) / utilities.get_pak_dir_structure(mod_name)
    final_dest_dir = Path(utilities.custom_get_game_paks_dir() / utilities.get_pak_dir_structure(mod_name))
    extensions = data_structures.unreal_iostore_no_sigs_archive_extensions

    dest_prefix = f"{final_dest_dir}/{mod_name}."
    output_mod_prefix = f"{intermediate_dest_dir}/{mod_name}."
    intermediate_dest_dir.mkdir(parents=True, exist_ok=True)
    Path(utilities.custom_get_game_paks_dir() / utilities.get_pak_dir_structure(mod_name)).mkdir(parents=True, exist_ok=True)

    for extension in extensions:
        output_file = Path(f"{output_mod_prefix}{extension}")
        if output_file.is_file() or output_file.is_symlink():
            output_file.unlink()

    make_retoc_mod(
        mod_name, Path(f"{output_mod_prefix}pak"), use_symlinks=use_symlinks,
    )

    for extension in extensions:
        dest_file = Path(f"{dest_prefix}{extension}")
        output_file = Path(f"{output_mod_prefix}{extension}")

        if use_symlinks:
            dest_file.symlink_to(output_file)
        else:
            shutil.copy(output_file, dest_file)


def run_gen_script_objects_retoc_command(
    retoc_executable: Path,
    jmap_file: Path,
    output: Path,
) -> None:
    args = [
        "gen-script-objects",
        "--version",
        settings.get_unreal_engine_version(settings.get_unreal_engine_dir()).get_retoc_unreal_version_str(), # ty: ignore
        jmap_file,
        output,
    ]

    app_runner.run_app(
        exe_path=retoc_executable,
        exec_mode=data_structures.ExecutionMode.SYNC,
        args=args,
    )
