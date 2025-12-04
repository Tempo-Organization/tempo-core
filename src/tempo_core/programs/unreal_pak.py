import os
import shutil

import tempo_core.settings
import tempo_core.app_runner
from tempo_core.programs import unreal_engine
from tempo_core import file_io, packing, utilities
from tempo_core.data_structures import CompressionType


def get_pak_dir_to_pack(mod_name: str):
    return f"{tempo_core.settings.get_temp_directory()}/{mod_name}"


def make_response_file_iostore(mod_name: str) -> str:
    file_list_path = os.path.join(
        tempo_core.settings.get_temp_directory(), f"{mod_name}_filelist.txt"
    )
    dir_to_pack = get_pak_dir_to_pack(mod_name)
    processed_base_paths = set()

    with open(file_list_path, "w") as file:
        for root, _, files in os.walk(dir_to_pack):
            for file_name in files:
                absolute_path = os.path.join(root, file_name)
                if not os.path.isfile(absolute_path):
                    file_not_found_error = (
                        f'The following file could not be found "{absolute_path}"'
                    )
                    raise FileNotFoundError(file_not_found_error)

                base_path = os.path.splitext(absolute_path)[0]
                if base_path in processed_base_paths:
                    continue

                processed_base_paths.add(base_path)

                relative_path = os.path.relpath(root, dir_to_pack).replace("\\", "/")
                mount_point = f"../../../{relative_path}/"
                file.write(f'"{os.path.normpath(absolute_path)}" "{mount_point}"\n')
    return file_list_path


def make_response_file_non_iostore(mod_name: str) -> str:
    file_list_path = os.path.join(
        tempo_core.settings.get_temp_directory(), f"{mod_name}_filelist.txt"
    )
    dir_to_pack = get_pak_dir_to_pack(mod_name)
    with open(file_list_path, "w") as file:
        for root, _, files in os.walk(dir_to_pack):
            for file_name in files:
                absolute_path = os.path.join(root, file_name)
                if not os.path.isfile:
                    file_not_found_error = (
                        f'The following file could not be found "{absolute_path}"'
                    )
                    raise FileNotFoundError(file_not_found_error)
                relative_path = os.path.relpath(root, dir_to_pack).replace("\\", "/")
                mount_point = f"../../../{relative_path}/"
                file.write(f'"{os.path.normpath(absolute_path)}" "{mount_point}"\n')
    return file_list_path


def get_iostore_commands_file_contents(mod_name: str, dest_pak_file: str) -> str:
    chunk_utoc = os.path.normpath(f"{os.path.dirname(dest_pak_file)}/{mod_name}.utoc")
    container_name = mod_name
    response_file = make_response_file_iostore(mod_name)
    return f'''-Output="{chunk_utoc}" -ContainerName={container_name} -ResponseFile="{response_file}"'''


# seems like it doesn't makes pak files rn, check it filters the files
def make_ue4_iostore_mod(
    *,
    exe_path: str,
    intermediate_pak_file: str,
    mod_name: str,
    compression_str: str | None,
    dest_pak_file: str,
    use_symlinks: bool,
):
    print(f'intermediate pak file path: "{intermediate_pak_file}"')
    print(f'destination pak file: "{dest_pak_file}"')

    # installs packing tool if need be,
    # moves files from various locations over to temp packaging location,
    # makes dirs as need be,
    # makes mod in intermediate location, for paks and iostore, using only the relevant files for each,
    # copies or symlinks files over to final location
    # destroy temp dir on program start

    temp_dir = tempo_core.settings.get_temp_directory()
    unreal_engine_dir = tempo_core.settings.get_unreal_engine_dir()
    unreal_engine_editor_cmd_executable_path = unreal_engine.get_editor_cmd_path(
        str(unreal_engine_dir)
    )
    ue_win_dir_str = unreal_engine.get_win_dir_str(str(unreal_engine_dir))
    uproject_dir = utilities.get_uproject_dir()
    uproject_file = tempo_core.settings.get_uproject_file()
    if not uproject_file:
        raise FileNotFoundError("uproject file returned None at a critical time")
    uproject_name = os.path.splitext(os.path.basename(uproject_file))[0]

    global_utoc_path = os.path.normpath(
        f"{uproject_dir}/Saved/StagedBuilds/{ue_win_dir_str}/{uproject_name}/Content/Paks/global.utoc"
    )
    cooked_content_dir = os.path.normpath(f"{temp_dir}/{mod_name}")

    # the below code line is how unreal knows where to place the output mod files, and does not account for intermediate locations currently
    # have it make them in the intermediate location, then do copy/symlink over after

    commands_txt_content = get_iostore_commands_file_contents(
        mod_name, intermediate_pak_file
    )
    # commands_txt_content = get_iostore_commands_file_contents(mod_name, dest_pak_file)

    commands_txt_path = os.path.normpath(
        f"{temp_dir}/iostore_packaging/{mod_name}_commands_list.txt"
    )
    commands_txt_dir = os.path.dirname(commands_txt_path)
    os.makedirs(commands_txt_dir, exist_ok=True)
    with open(commands_txt_path, "w") as file:
        file.write(commands_txt_content)

    src_metadata_dir = os.path.normpath(
        f"{uproject_dir}/Saved/Cooked/{ue_win_dir_str}/{uproject_name}/Metadata"
    )
    dest_metadata_dir = os.path.normpath(
        f"{temp_dir}/{mod_name}/{uproject_name}/Metadata"
    )

    os.makedirs(src_metadata_dir, exist_ok=True)

    # crypto_keys_json = os.path.normpath(f"{src_metadata_dir}/Crypto.json")

    src_ubulk_manifest = os.path.normpath(
        f"{src_metadata_dir}/BulkDataInfo.ubulkmanifest"
    )
    dest_ubulk_manifest = os.path.normpath(
        f"{dest_metadata_dir}/BulkDataInfo.ubulkmanifest"
    )

    if os.path.isfile(dest_ubulk_manifest):
        os.remove(dest_ubulk_manifest)

    os.makedirs(os.path.dirname(dest_ubulk_manifest), exist_ok=True)

    file_io.verify_directories_exists(
        [cooked_content_dir, src_metadata_dir, str(unreal_engine_dir)]
    )
    file_io.verify_files_exists(
        [
            # global_utoc_path,
            # crypto_keys_json,
            commands_txt_path,
            src_ubulk_manifest,
            # unreal_engine_editor_cmd_executable_path,
            str(uproject_file),
        ]
    )

    shutil.copy(src_ubulk_manifest, dest_ubulk_manifest)

    iostore_txt_location = os.path.normpath(
        f"{tempo_core.settings.get_temp_directory()}/iostore_packaging/{mod_name}_iostore.txt"
    )
    # default_engine_patch_padding_alignment = 2048
    args = [
        # unreal_pak,
        f'"{uproject_file}"',
        "-run=IoStore",
        f'-CreateGlobalContainer="{global_utoc_path}"',
        f'-CookedDirectory="{cooked_content_dir}"',
        f'-Commands="{commands_txt_path}"',
        # f'-CookerOrder="{os.path.normpath(cooker_order_file)}"',
        # f'-patchpaddingalign={default_engine_patch_padding_alignment}',
        "-NoDirectoryIndex",
        # f'-cryptokeys="{os.path.normpath(crypto_keys_json)}"',
        f"-TargetPlatform={ue_win_dir_str}",
        f'-abslog="{iostore_txt_location}"',
        "-stdout",
        "-CrashForUAT",
        "-unattended",
        "-NoLogTimes",
        "-UTF8Output",
    ]
    tempo_core.app_runner.run_app(
        exe_path=unreal_engine_editor_cmd_executable_path, args=args
    )

    intermediary_utoc_file = os.path.normpath(
        f"{os.path.dirname(intermediate_pak_file)}/{mod_name}.utoc"
    )
    intermediate_ucas_file = os.path.normpath(
        f"{os.path.dirname(intermediate_pak_file)}/{mod_name}.ucas"
    )

    dest_utoc_file = os.path.normpath(
        f"{os.path.dirname(dest_pak_file)}/{mod_name}.utoc"
    )
    dest_ucas_file = os.path.normpath(
        f"{os.path.dirname(dest_pak_file)}/{mod_name}.ucas"
    )

    if os.path.isfile(intermediary_utoc_file):
        print("chunk utoc was file")
        print(f'chunk utoc location: "{intermediary_utoc_file}"')
    else:
        missing_intermediary_chunk_utoc_error = f'chunk utoc file was not found at the following location: "{intermediary_utoc_file}"'
        raise FileNotFoundError(missing_intermediary_chunk_utoc_error)

    if os.path.isfile(intermediate_ucas_file):
        print("chunk utoc was file")
        print(f'chunk utoc location: "{intermediate_ucas_file}"')
    else:
        missing_intermediary_chunk_ucas_error = f'chunk ucas file was not found at the following location: "{intermediate_ucas_file}"'
        raise FileNotFoundError(missing_intermediary_chunk_ucas_error)

    if use_symlinks:
        os.symlink(intermediary_utoc_file, dest_utoc_file)
    else:
        shutil.copyfile(intermediary_utoc_file, dest_utoc_file)

    if use_symlinks:
        os.symlink(intermediate_ucas_file, dest_ucas_file)
    else:
        shutil.copyfile(intermediate_ucas_file, dest_ucas_file)

    # if use_symlinks:
    #     os.symlink(intermediate_pak_file, dest_pak_file)
    # else:
    #     shutil.copyfile(intermediate_pak_file, dest_pak_file)


def make_ue5_iostore_mods(
    *,
    exe_path: str,
    intermediate_pak_file: str,
    mod_name: str,
    compression_str: str | None,
    dest_pak_file: str,
    use_symlinks: bool,
):
    unreal_engine_dir = tempo_core.settings.get_unreal_engine_dir()
    # unreal_pak = unreal_engine.get_unreal_pak_exe_path(unreal_engine_dir)
    unreal_engine_editor_cmd_executable_path = unreal_engine.get_editor_cmd_path(
        str(unreal_engine_dir)
    )
    ue_win_dir_str = unreal_engine.get_win_dir_str(str(unreal_engine_dir))
    uproject_name = tempo_core.settings.get_uproject_name()
    if not uproject_name:
        raise FileNotFoundError("uproject name returned None at a critical moment")
    uproject_file = tempo_core.settings.get_uproject_file()
    global_utoc_path = f"{utilities.get_uproject_dir()}/Saved/StagedBuilds/{ue_win_dir_str}/{uproject_name}/Content/Paks/global.utoc"
    cooked_content_dir = f"{tempo_core.settings.get_temp_directory()}/{mod_name}"

    commands_txt_content = get_iostore_commands_file_contents(mod_name, dest_pak_file)
    commands_txt_path = f"{tempo_core.settings.get_temp_directory()}/iostore_packaging/{mod_name}_commands_list.txt"
    os.makedirs(os.path.dirname(commands_txt_path), exist_ok=True)
    with open(commands_txt_path, "w") as file:
        file.write(commands_txt_content)

    meta_data_dir = f"{utilities.get_uproject_dir()}/Saved/Cooked/{ue_win_dir_str}/{uproject_name}/Metadata"
    crypto_keys_json = f"{meta_data_dir}/Crypto.json"
    script_objects_bin = f"{meta_data_dir}/scriptobjects.bin"
    package_store_manifest = f"{meta_data_dir}/packagestore.manifest"
    src_ubulk_manifest = f"{meta_data_dir}/BulkDataInfo.ubulkmanifest"
    dest_ubulk_manifest = os.path.normpath(
        f"{meta_data_dir}/BulkDataInfo.ubulkmanifest"
    )

    if os.path.isfile(dest_ubulk_manifest):
        os.remove(dest_ubulk_manifest)

    dest_ubulk_manifest_dir = os.path.dirname(dest_ubulk_manifest)

    os.makedirs(dest_ubulk_manifest_dir, exist_ok=True)

    file_io.verify_directories_exists(
        [cooked_content_dir, str(unreal_engine_dir), meta_data_dir]
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
        ]
    )

    shutil.copy(src_ubulk_manifest, dest_ubulk_manifest)

    platform_string = unreal_engine.get_win_dir_str(
        str(tempo_core.settings.get_unreal_engine_dir())
    )
    iostore_txt_location = os.path.normpath(
        f"{tempo_core.settings.get_temp_directory()}/iostore_packaging/{mod_name}_iostore.txt"
    )
    # default_engine_patch_padding_alignment = 2048
    args = [
        # f'"{unreal_pak}',
        f'"{uproject_file}"',
        "-run=IoStore",
        f'-CreateGlobalContainer="{os.path.normpath(global_utoc_path)}"',
        f'-CookedDirectory="{os.path.normpath(cooked_content_dir)}"',
        f'-Commands="{os.path.normpath(commands_txt_path)}"',
        f'-PackageStoreManifest="{package_store_manifest}"',
        f'-ScriptObjects="{script_objects_bin}"',
        # f'-CookerOrder="{os.path.normpath(cooker_order_file)}"',
        # f'-patchpaddingalign={default_engine_patch_padding_alignment}',
        "-NoDirectoryIndex",
        # f'-cryptokeys="{os.path.normpath(crypto_keys_json)}"',
        f"-TargetPlatform={platform_string}",
        f'-abslog="{iostore_txt_location}"',
        "-stdout",
        "-CrashForUAT",
        "-unattended",
        "-NoLogTimes",
        "-UTF8Output",
    ]
    tempo_core.app_runner.run_app(
        exe_path=unreal_engine_editor_cmd_executable_path, args=args
    )


# at this point it seems mostly done outside of intermediary pak location/symlink support, as well as ubulk copying from the uproject
def make_iostore_unreal_pak_mod(
    *,
    exe_path: str,
    intermediate_pak_file: str,
    mod_name: str,
    compression_str: str | None,
    dest_pak_file: str,
    use_symlinks: bool,
):
    if unreal_engine.is_game_ue4(str(tempo_core.settings.get_unreal_engine_dir())):
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
    exe_path: str,
    intermediate_pak_file: str,
    mod_name: str,
    compression_str: str | None,
    dest_pak_file: str,
    use_symlinks: bool,
):
    command = f'"{exe_path}" "{intermediate_pak_file}" -Create="{make_response_file_non_iostore(mod_name)}"'
    if compression_str != "None" and compression_str:
        # find out which version compressed instead of compressed was added and pass either based on that
        command = f"{command} -compress -compressionformat={compression_str}"
    tempo_core.app_runner.run_app(command)
    if os.path.islink(dest_pak_file):
        os.unlink(dest_pak_file)
    if os.path.isfile(dest_pak_file):
        os.remove(dest_pak_file)
    packing.install_mod_sig(mod_name, use_symlinks=use_symlinks)
    if use_symlinks:
        os.symlink(intermediate_pak_file, dest_pak_file)
    else:
        shutil.copyfile(intermediate_pak_file, dest_pak_file)


def install_unreal_pak_mod(
    mod_name: str, compression_type: CompressionType | None, *, use_symlinks: bool
):
    move_files_for_packing(mod_name)
    # add a check for if compression type is None here
    if compression_type:
        compression_str = CompressionType(compression_type).value
    else:
        compression_str = None
    output_pak_dir = f"{tempo_core.settings.get_temp_directory()}/{utilities.get_pak_dir_structure(mod_name)}"
    intermediate_pak_file = f"{tempo_core.settings.get_temp_directory()}/{utilities.get_pak_dir_structure(mod_name)}/{mod_name}.pak"
    dest_pak_file = f"{utilities.custom_get_game_paks_dir()}/{utilities.get_pak_dir_structure(mod_name)}/{mod_name}.pak"
    os.makedirs(output_pak_dir, exist_ok=True)
    os.makedirs(
        f"{utilities.custom_get_game_paks_dir()}/{utilities.get_pak_dir_structure(mod_name)}",
        exist_ok=True,
    )
    exe_path = unreal_engine.get_unreal_pak_exe_path(
        str(tempo_core.settings.get_unreal_engine_dir())
    )
    uproject_file = tempo_core.settings.get_uproject_file()
    if not uproject_file:
        raise FileNotFoundError("get uproject file returned None at a critical moment")
    is_game_iostore = unreal_engine.get_is_game_iostore(
        str(uproject_file), utilities.custom_get_game_dir()
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


def move_files_for_packing(mod_name: str):
    from tempo_core import settings

    should_use_progress_bars = settings.should_show_progress_bars()
    mod_files_dict = packing.get_mod_file_paths_for_manually_made_pak_mods(mod_name)
    mod_files_dict = utilities.filter_file_paths(mod_files_dict)

    def copy_files():
        for src_file, dest_file in mod_files_dict.items():
            dest_dir = os.path.dirname(dest_file)

            if os.path.exists(dest_file):
                if not file_io.get_do_files_have_same_hash(src_file, dest_file):
                    os.remove(dest_file)
            elif not os.path.isdir(dest_dir):
                os.makedirs(dest_dir)

            if os.path.isfile(src_file):
                shutil.copy2(src_file, dest_file)

    if should_use_progress_bars:
        from rich.progress import Progress

        with Progress() as progress:
            task = progress.add_task(
                f"[green]Copying files for {mod_name} mod...", total=len(mod_files_dict)
            )
            for src_file, dest_file in mod_files_dict.items():
                dest_dir = os.path.dirname(dest_file)

                if os.path.exists(dest_file):
                    if not file_io.get_do_files_have_same_hash(src_file, dest_file):
                        os.remove(dest_file)
                elif not os.path.isdir(dest_dir):
                    os.makedirs(dest_dir)

                if os.path.isfile(src_file):
                    shutil.copy2(src_file, dest_file)

                progress.update(task, advance=1)
    else:
        copy_files()
