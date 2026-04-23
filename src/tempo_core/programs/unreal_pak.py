import os
import shutil
from pathlib import Path

import tempo_core.settings
import tempo_core.app_runner
from tempo_core.programs import unreal_engine
from tempo_core import file_io, packing, utilities, logger
from tempo_core.data_structures import CompressionType


def get_pak_dir_to_pack(mod_name: str) -> Path:
    return Path(tempo_core.settings.get_temp_directory() / mod_name)


def make_response_file_iostore(mod_name: str) -> Path:
    file_list_path = Path(tempo_core.settings.get_temp_directory() / f"{mod_name}_filelist.txt")
    dir_to_pack = get_pak_dir_to_pack(mod_name)
    processed_base_paths = set()

    with file_list_path.open("w") as file:
        for root, _, files in dir_to_pack.walk():
            for file_name in files:
                absolute_path = Path(root / file_name)
                if not absolute_path.is_file():
                    file_not_found_error = (
                        f'The following file could not be found "{absolute_path}"'
                    )
                    raise FileNotFoundError(file_not_found_error)

                base_path = absolute_path.with_suffix('')
                if base_path in processed_base_paths:
                    continue

                processed_base_paths.add(base_path)

                relative_path = os.path.relpath(root, dir_to_pack).replace("\\", "/")
                mount_point = f"../../../{relative_path}/"
                file.write(f'"{Path(absolute_path)}" "{mount_point}"\n')
    return file_list_path


def make_response_file_non_iostore(mod_name: str) -> Path:
    file_list_path = Path(tempo_core.settings.get_temp_directory(), f"{mod_name}_filelist.txt")
    dir_to_pack = get_pak_dir_to_pack(mod_name)
    with file_list_path.open("w") as file:
        for root, _, files in dir_to_pack.walk():
            for file_name in files:
                absolute_path = Path(root / file_name)
                if not os.path.isfile:
                    file_not_found_error = (
                        f'The following file could not be found "{absolute_path}"'
                    )
                    raise FileNotFoundError(file_not_found_error)
                relative_path = os.path.relpath(root, dir_to_pack).replace("\\", "/")
                mount_point = f"../../../{relative_path}/"
                file.write(f'"{Path(absolute_path)}" "{mount_point}"\n')
    return file_list_path


def get_iostore_commands_file_contents(mod_name: str, dest_pak_file: Path) -> str:
    chunk_utoc = Path(dest_pak_file.parent / f"{mod_name}.utoc")
    container_name = mod_name
    response_file = make_response_file_iostore(mod_name)
    return f'''-Output="{chunk_utoc}" -ContainerName={container_name} -ResponseFile="{response_file}"'''


# seems like it doesn't makes pak files rn, check it filters the files
def make_ue4_iostore_mod(
    *,
    exe_path: Path,
    intermediate_pak_file: Path,
    mod_name: str,
    compression_str: str | None,
    dest_pak_file: Path,
    use_symlinks: bool,
) -> None:
    logger.log_message(f'intermediate pak file path: "{intermediate_pak_file}"')
    logger.log_message(f'destination pak file: "{dest_pak_file}"')

    # installs packing tool if need be,
    # moves files from various locations over to temp packaging location,
    # makes dirs as need be,
    # makes mod in intermediate location, for paks and iostore, using only the relevant files for each,
    # copies or symlinks files over to final location
    # destroy temp dir on program start

    temp_dir = tempo_core.settings.get_temp_directory()
    unreal_engine_dir = tempo_core.settings.get_unreal_engine_dir()
    if not unreal_engine_dir:
        raise RuntimeError('Unreal engine install was not valid.')
    unreal_engine_editor_cmd_executable_path = unreal_engine.get_editor_cmd_path(unreal_engine_dir)
    ue_win_dir_str = unreal_engine.get_win_dir_str(unreal_engine_dir)
    uproject_dir = utilities.get_uproject_dir()
    if not uproject_dir:
        raise RuntimeError('Uproject directory was not valid.')
    uproject_file = tempo_core.settings.get_uproject_file()
    if not uproject_file:
        raise FileNotFoundError("uproject file returned None at a critical time")
    uproject_name = Path(uproject_file.name).stem

    global_utoc_path = Path(
        f"{uproject_dir}/Saved/StagedBuilds/{ue_win_dir_str}/{uproject_name}/Content/Paks/global.utoc",
    )
    cooked_content_dir = Path(temp_dir / mod_name)

    # the below code line is how unreal knows where to place the output mod files, and does not account for intermediate locations currently
    # have it make them in the intermediate location, then do copy/symlink over after

    commands_txt_content = get_iostore_commands_file_contents(
        mod_name, intermediate_pak_file,
    )
    # commands_txt_content = get_iostore_commands_file_contents(mod_name, dest_pak_file)

    commands_txt_path = Path(temp_dir / 'iostore_packaging' / f'{mod_name}_commands_list.txt')
    commands_txt_dir = commands_txt_path.parent
    commands_txt_dir.mkdir(parents=True, exist_ok=True)
    with commands_txt_path.open("w") as file:
        file.write(commands_txt_content)

    src_metadata_dir = Path(uproject_dir / 'Saved/Cooked' / ue_win_dir_str / uproject_name / 'Metadata')
    dest_metadata_dir = Path(temp_dir / mod_name / uproject_name / 'Metadata')

    src_metadata_dir.mkdir(parents=True, exist_ok=True)

    # crypto_keys_json = Path(f"{src_metadata_dir}/Crypto.json")

    src_ubulk_manifest = Path(src_metadata_dir / 'BulkDataInfo.ubulkmanifest')
    dest_ubulk_manifest = Path(dest_metadata_dir / 'BulkDataInfo.ubulkmanifest')

    if dest_ubulk_manifest.is_file():
        dest_ubulk_manifest.unlink()

    dest_ubulk_manifest.parent.mkdir(parents=True, exist_ok=True)

    file_io.verify_directories_exists(
        [cooked_content_dir, src_metadata_dir, unreal_engine_dir],
    )
    file_io.verify_files_exists(
        [
            # global_utoc_path,
            # crypto_keys_json,
            commands_txt_path,
            src_ubulk_manifest,
            # unreal_engine_editor_cmd_executable_path,
            uproject_file,
        ],
    )

    shutil.copy(src_ubulk_manifest, dest_ubulk_manifest)

    iostore_txt_location = Path(
        f"{tempo_core.settings.get_temp_directory()}/iostore_packaging/{mod_name}_iostore.txt",
    )
    # default_engine_patch_padding_alignment = 2048
    args = [
        # unreal_pak,
        f'"{uproject_file}"',
        "-run=IoStore",
        f'-CreateGlobalContainer="{global_utoc_path}"',
        f'-CookedDirectory="{cooked_content_dir}"',
        f'-Commands="{commands_txt_path}"',
        # f'-CookerOrder="{Path(cooker_order_file)}"',
        # f'-patchpaddingalign={default_engine_patch_padding_alignment}',
        "-NoDirectoryIndex",
        # f'-cryptokeys="{Path(crypto_keys_json)}"',
        f"-TargetPlatform={ue_win_dir_str}",
        f'-abslog="{iostore_txt_location}"',
        "-stdout",
        "-CrashForUAT",
        "-unattended",
        "-NoLogTimes",
        "-UTF8Output",
    ]
    tempo_core.app_runner.run_app(
        exe_path=unreal_engine_editor_cmd_executable_path, args=args,
    )

    intermediary_utoc_file = Path(
        f"{intermediate_pak_file.parent}/{mod_name}.utoc",
    )
    intermediate_ucas_file = Path(
        f"{intermediate_pak_file.parent}/{mod_name}.ucas",
    )

    dest_utoc_file = Path(
        f"{dest_pak_file.parent}/{mod_name}.utoc",
    )
    dest_ucas_file = Path(
        f"{dest_pak_file.parent}/{mod_name}.ucas",
    )

    if intermediary_utoc_file.is_file():
        logger.log_message("chunk utoc was file")
        logger.log_message(f'chunk utoc location: "{intermediary_utoc_file}"')
    else:
        missing_intermediary_chunk_utoc_error = f'chunk utoc file was not found at the following location: "{intermediary_utoc_file}"'
        raise FileNotFoundError(missing_intermediary_chunk_utoc_error)

    if intermediate_ucas_file.is_file():
        logger.log_message("chunk utoc was file")
        logger.log_message(f'chunk utoc location: "{intermediate_ucas_file}"')
    else:
        missing_intermediary_chunk_ucas_error = f'chunk ucas file was not found at the following location: "{intermediate_ucas_file}"'
        raise FileNotFoundError(missing_intermediary_chunk_ucas_error)

    if use_symlinks:
        intermediary_utoc_file.symlink_to(dest_utoc_file)
    else:
        shutil.copyfile(intermediary_utoc_file, dest_utoc_file)

    if use_symlinks:
        intermediate_ucas_file.symlink_to(dest_ucas_file)
    else:
        shutil.copyfile(intermediate_ucas_file, dest_ucas_file)

    # if use_symlinks:
    #     os.symlink(intermediate_pak_file, dest_pak_file)
    # else:
    #     shutil.copyfile(intermediate_pak_file, dest_pak_file)


def make_ue5_iostore_mods(
    *,
    exe_path: Path,
    intermediate_pak_file: Path,
    mod_name: str,
    compression_str: str | None,
    dest_pak_file: Path,
    use_symlinks: bool,
) -> None:
    unreal_engine_dir = tempo_core.settings.get_unreal_engine_dir()
    if not unreal_engine_dir:
        raise RuntimeError('Unreal engine install was not valid.')
    # unreal_pak = unreal_engine.get_unreal_pak_exe_path(unreal_engine_dir)
    unreal_engine_editor_cmd_executable_path = unreal_engine.get_editor_cmd_path(unreal_engine_dir)
    ue_win_dir_str = unreal_engine.get_win_dir_str(unreal_engine_dir)
    uproject_name = tempo_core.settings.get_uproject_name()
    if not uproject_name:
        raise FileNotFoundError("uproject name returned None at a critical moment")
    uproject_file = tempo_core.settings.get_uproject_file()
    global_utoc_path = Path(f"{utilities.get_uproject_dir()}/Saved/StagedBuilds/{ue_win_dir_str}/{uproject_name}/Content/Paks/global.utoc")
    cooked_content_dir = Path(f"{tempo_core.settings.get_temp_directory()}/{mod_name}")

    commands_txt_content = get_iostore_commands_file_contents(mod_name, dest_pak_file)
    commands_txt_path = Path(tempo_core.settings.get_temp_directory() / 'iostore_packaging' / f'{mod_name}_commands_list.txt')
    commands_txt_path.parent.mkdir(parents=True, exist_ok=True)
    with commands_txt_path.open("w") as file:
        file.write(commands_txt_content)

    meta_data_dir = Path(f"{utilities.get_uproject_dir()}/Saved/Cooked/{ue_win_dir_str}/{uproject_name}/Metadata")
    crypto_keys_json = Path(f"{meta_data_dir}/Crypto.json")
    script_objects_bin = Path(f"{meta_data_dir}/scriptobjects.bin")
    package_store_manifest = Path(f"{meta_data_dir}/packagestore.manifest")
    src_ubulk_manifest = Path(f"{meta_data_dir}/BulkDataInfo.ubulkmanifest")
    dest_ubulk_manifest = Path(
        f"{meta_data_dir}/BulkDataInfo.ubulkmanifest",
    )

    if dest_ubulk_manifest.is_file():
        dest_ubulk_manifest.unlink()

    dest_ubulk_manifest_dir = dest_ubulk_manifest.parent

    dest_ubulk_manifest_dir.mkdir(parents=True, exist_ok=True)

    file_io.verify_directories_exists(
        [cooked_content_dir, unreal_engine_dir, meta_data_dir],
    )
    file_io.verify_files_exists(
        [
            global_utoc_path,
            crypto_keys_json,
            commands_txt_path,
            src_ubulk_manifest,
            unreal_engine_editor_cmd_executable_path,
            package_store_manifest,
            script_objects_bin,
        ],
    )

    shutil.copy(src_ubulk_manifest, dest_ubulk_manifest)

    platform_string = unreal_engine.get_win_dir_str(tempo_core.settings.get_unreal_engine_dir())
    iostore_txt_location = Path(
        f"{tempo_core.settings.get_temp_directory()}/iostore_packaging/{mod_name}_iostore.txt",
    )
    # default_engine_patch_padding_alignment = 2048
    args = [
        # f'"{unreal_pak}',
        f'"{uproject_file}"',
        "-run=IoStore",
        f'-CreateGlobalContainer="{global_utoc_path}"',
        f'-CookedDirectory="{cooked_content_dir}"',
        f'-Commands="{commands_txt_path}"',
        f'-PackageStoreManifest="{package_store_manifest}"',
        f'-ScriptObjects="{script_objects_bin}"',
        # f'-CookerOrder="{Path(cooker_order_file)}"',
        # f'-patchpaddingalign={default_engine_patch_padding_alignment}',
        "-NoDirectoryIndex",
        # f'-cryptokeys="{Path(crypto_keys_json)}"',
        f"-TargetPlatform={platform_string}",
        f'-abslog="{iostore_txt_location}"',
        "-stdout",
        "-CrashForUAT",
        "-unattended",
        "-NoLogTimes",
        "-UTF8Output",
    ]
    tempo_core.app_runner.run_app(
        exe_path=unreal_engine_editor_cmd_executable_path, args=args,
    )


# at this point it seems mostly done outside of intermediary pak location/symlink support, as well as ubulk copying from the uproject
def make_iostore_unreal_pak_mod(
    *,
    exe_path: Path,
    intermediate_pak_file: Path,
    mod_name: str,
    compression_str: str | None,
    dest_pak_file: Path,
    use_symlinks: bool,
) -> None:
    if unreal_engine.is_game_ue4(tempo_core.settings.get_unreal_engine_dir()):
        make_ue4_iostore_mod(
            mod_name=mod_name,
            exe_path=exe_path,
            intermediate_pak_file=intermediate_pak_file,
            compression_str=compression_str,
            dest_pak_file=dest_pak_file,
            use_symlinks=use_symlinks,
        )
    else:
        make_ue5_iostore_mods(
            mod_name=mod_name,
            exe_path=exe_path,
            intermediate_pak_file=intermediate_pak_file,
            compression_str=compression_str,
            dest_pak_file=dest_pak_file,
            use_symlinks=use_symlinks,
        )


def make_non_iostore_unreal_pak_mod(
    *,
    exe_path: Path,
    intermediate_pak_file: Path,
    mod_name: str,
    compression_str: str | None,
    dest_pak_file: Path,
    use_symlinks: bool,
) -> None:
    args = [
        f'"{intermediate_pak_file}"',
        f'-Create="{make_response_file_non_iostore(mod_name)}"',
    ]
    if compression_str != "None" and compression_str:
        # find out which version compressed instead of compressed was added and pass either based on that
        args.extend(['-compress', f'-compressionformat={compression_str}'])
    tempo_core.app_runner.run_app(exe_path=exe_path, args=args)
    if Path.is_symlink(dest_pak_file):
        dest_pak_file.unlink()
    if dest_pak_file.is_file():
        dest_pak_file.unlink()
    packing.install_mod_sig(mod_name, use_symlinks=use_symlinks)
    if use_symlinks:
        intermediate_pak_file.symlink_to(dest_pak_file)
    else:
        shutil.copyfile(intermediate_pak_file, dest_pak_file)


def install_unreal_pak_mod(
    mod_name: str, compression_type: CompressionType | None, *, use_symlinks: bool,
) -> None:
    move_files_for_packing(mod_name)
    # add a check for if compression type is None here
    if compression_type:
        compression_str = CompressionType(compression_type).value
    else:
        compression_str = None
    output_pak_dir = Path(f"{tempo_core.settings.get_temp_directory()}/{utilities.get_pak_dir_structure(mod_name)}")
    intermediate_pak_file = Path(f"{tempo_core.settings.get_temp_directory()}/{utilities.get_pak_dir_structure(mod_name)}/{mod_name}.pak")
    dest_pak_file = Path(f"{utilities.custom_get_game_paks_dir()}/{utilities.get_pak_dir_structure(mod_name)}/{mod_name}.pak")
    output_pak_dir.mkdir(parents=True, exist_ok=True)
    Path(f"{utilities.custom_get_game_paks_dir()}/{utilities.get_pak_dir_structure(mod_name)}").mkdir(exist_ok=True)
    unreal_engine_dir = tempo_core.settings.get_unreal_engine_dir()
    if not unreal_engine_dir:
        raise RuntimeError('Unreal engine install was not valid.')
    exe_path = unreal_engine.get_unreal_pak_exe_path(unreal_engine_dir)
    uproject_file = tempo_core.settings.get_uproject_file()
    if not uproject_file:
        raise FileNotFoundError("get uproject file returned None at a critical moment")
    custom_game_dir = utilities.custom_get_game_dir()
    if not custom_game_dir:
        raise RuntimeError('custom_game_dir was not valid.')
    is_game_iostore = unreal_engine.get_is_game_iostore(
        uproject_file, custom_game_dir,
    )

    if is_game_iostore:
        make_iostore_unreal_pak_mod(
            mod_name=mod_name,
            exe_path=exe_path,
            intermediate_pak_file=intermediate_pak_file,
            compression_str=compression_str,
            dest_pak_file=dest_pak_file,
            use_symlinks=use_symlinks,
        )
    else:
        make_non_iostore_unreal_pak_mod(
            mod_name=mod_name,
            exe_path=exe_path,
            intermediate_pak_file=intermediate_pak_file,
            compression_str=compression_str,
            dest_pak_file=dest_pak_file,
            use_symlinks=use_symlinks,
        )


def move_files_for_packing(mod_name: str) -> None:
    from tempo_core import settings

    should_use_progress_bars = settings.should_show_progress_bars()
    mod_files_dict = packing.get_mod_file_paths_for_manually_made_pak_mods(mod_name)
    mod_files_dict = utilities.filter_file_paths(mod_files_dict)

    def copy_files() -> None:
        for src_file, dest_file in mod_files_dict.items():
            dest_dir = dest_file.parent

            if dest_file.exists():
                if not file_io.get_do_files_have_same_hash(src_file, dest_file):
                    dest_file.unlink()
            elif not dest_dir.is_dir():
                dest_dir.mkdir(parents=True)

            if src_file.is_file():
                shutil.copy2(src_file, dest_file)

    if should_use_progress_bars:
        from rich.progress import Progress

        with Progress() as progress:
            task = progress.add_task(
                f"[green]Copying files for {mod_name} mod...", total=len(mod_files_dict),
            )
            for src_file, dest_file in mod_files_dict.items():
                dest_dir = dest_file.parent

                if dest_file.exists():
                    if not file_io.get_do_files_have_same_hash(src_file, dest_file):
                        dest_file.unlink()
                elif not dest_dir.is_dir():
                    dest_dir.mkdir(parents=True)

                if src_file.is_file():
                    shutil.copy2(src_file, dest_file)

                progress.update(task, advance=1)
    else:
        copy_files()
