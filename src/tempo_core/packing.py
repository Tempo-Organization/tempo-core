import os
import shutil
from pathlib import Path, PurePath
from dataclasses import dataclass

from rich.progress import Progress

from tempo_core import (
    app_runner,
    data_structures,
    file_io,
    hook_states,
    logger,
    settings,
    utilities,
)
from tempo_core.data_structures import (
    CompressionType,
    HookStateType,
    PackingType,
    get_enum_from_val,
)
from tempo_core.programs import repak, retoc, unreal_engine, unreal_pak


@dataclass
class QueueInformation:
    install_queue_types: set[PackingType]
    uninstall_queue_types: set[PackingType]


queue_information = QueueInformation(install_queue_types=set(), uninstall_queue_types=set())


command_queue = []


def populate_queue_information() -> None:

    mod_info_dict = settings.get_mods_info_dict_from_json()

    for mod_name in settings.get_enabled_mod_names():
        install_queue_type = get_enum_from_val(PackingType, mod_info_dict[mod_name]["packing_type"])
        queue_information.install_queue_types.add(install_queue_type)

    for mod_name in settings.get_disabled_mod_names():
        uninstall_queue_type = get_enum_from_val(PackingType, mod_info_dict[mod_name]["packing_type"])
        queue_information.uninstall_queue_types.add(uninstall_queue_type)


def get_mod_packing_type(mod_name: str) -> PackingType:
    mods_info_dict = settings.get_mods_info_dict_from_json()
    for mod_key in mods_info_dict.keys():
        if mod_name == mod_key:
            return PackingType(get_enum_from_val(PackingType, mods_info_dict[mod_key]["packing_type"]))
    invalid_packing_type_error = "invalid packing type found in config file"
    raise RuntimeError(invalid_packing_type_error)


def get_is_mod_name_in_use(mod_name: str) -> bool:
    return any(
        mod_name == mod_key
        for mod_key in settings.get_mods_info_dict_from_json().keys()
    )


# not sure if I fixed this right
def get_mod_pak_entry(mod_name: str) -> dict:
    mods_info_dict = settings.get_mods_info_dict_from_json()
    for mod_key in mods_info_dict.keys():
        if mod_key == mod_name:
            return dict(mods_info_dict[mod_key])
    return {}


def get_is_mod_installed(mod_name: str) -> bool:
    return any(
        mod_key == mod_name
        for mod_key in settings.get_mods_info_dict_from_json().keys()
    )


def get_engine_pak_command() -> list[str]:
    command = [
        f'"{unreal_engine.get_run_uat_script_path()}"',
        'BuildCookRun',
        f'-project="{settings.get_uproject_file_or_raise()}"',
    ]
    uproject_file = settings.get_uproject_file_or_raise()
    if not unreal_engine.has_build_target_been_built(uproject_file):
        command.append('-build')
    for arg in settings.get_engine_packaging_args():
        command.append(arg)
    custom_game_dir = utilities.get_game_dir_or_raise()
    is_game_iostore = unreal_engine.get_is_game_iostore(
        uproject_file, custom_game_dir,
    )
    if is_game_iostore:
        command.append('-iostore')
        logger.log_message("Check: Game is iostore")
    else:
        logger.log_message("Check: Game is not iostore")
    return command


# add support for collections later like this file_includes - unreal_collections
# make sure the right iterate command is being used based on correct versions later
def get_cook_project_commands() -> list[list[str]]:
    uproject_path = settings.get_uproject_file_or_raise()
    unreal_engine_dir = settings.get_unreal_engine_dir_or_raise()
    uproject_dir = utilities.get_uproject_dir_or_raise()

    if unreal_engine.is_game_ue4(unreal_engine_dir):
        single_cooking_arg = '-cooksinglepackage'
        partial_arg = '-Map='
    else:
        single_cooking_arg = '-cooksinglepackagenorefs'
        partial_arg = '-Package='

    command = [
        str(unreal_engine.get_editor_cmd_path(unreal_engine_dir)),
        str(uproject_path),
        '-run=cook',
        f'-targetplatform={settings.get_unreal_engine_target_platform()}',
        f'-clientconfig={settings.get_build_configuration_state()}',
        '-SkipCookingEditorContent',
        '-NODEV',
        '-iterative',
        '-fastcook',
        single_cooking_arg,
    ]

    mods_info = settings.get_mods_info_dict_from_json()

    asset_paths = []
    tree_paths = []
    mod_name_dir_type_paths = []

    for key in mods_info.keys():
        if mods_info[key].get('is_enabled', True) and mods_info[key]['packing_type'] != 'engine':
            asset_paths.extend(
                mods_info[key].get("file_includes", {}).get("asset_paths", []),
            )
            tree_paths.extend(
                mods_info[key].get("file_includes", {}).get("tree_paths", []),
            )

            if settings.get_should_mod_auto_include_mod_name_dir_name(key):
                path_to_check = f'{uproject_dir}/Content/Mods/{utilities.get_mod_name_dir_name(key)}'
                files_in_mod_name_dir_name_tree = file_io.get_files_in_tree(
                    Path(path_to_check),
                )

                for path in files_in_mod_name_dir_name_tree:
                    if path.is_file():
                        path_to_append = str(path.as_posix())
                        path_to_append = path_to_append.replace(
                            str(uproject_dir.as_posix()), "",
                        )
                        path_to_append = path_to_append.replace("Content", "Game", 1)
                        mod_name_dir_type_paths.append(path_to_append)

    final_file_list = []

    for path in asset_paths:
        final_file_list.append(path.replace("Content", "/Game", 1).as_posix())

    for path in tree_paths:
        full_path = f'{uproject_dir}/{path}'
        files_in_dir_tree = file_io.get_files_in_tree(Path(full_path))

        for file in files_in_dir_tree:
            if file.is_file():
                trimmed_path = str(file.as_posix()).replace(
                    str(uproject_dir.as_posix()), "",
                )
                trimmed_path = trimmed_path.replace("Content", "Game", 1)
                final_file_list.append(trimmed_path)

    final_file_list.extend(mod_name_dir_type_paths)

    maximum_command_length = utilities.get_maximum_command_length()

    max_length = (
        maximum_command_length
        - sum(len(arg) + 1 for arg in command)
        - 100
    )

    chunked_file_list = utilities.chunk_strings(final_file_list, max_length)

    commands_to_return = []

    for entry in chunked_file_list:
        command_args = command.copy()

        for file in entry:
            # command_args.append(f'{partial_arg}{os.path.splitext(file)[0]}')
            command_args.append(f'{partial_arg}{Path(file).stem}')

        commands_to_return.append(command_args)

    return commands_to_return


def build_uproject() -> None:
    from tempo_core import main_logic
    logger.log_message("Project Building Starting")
    run_proj_command(main_logic.get_solo_build_project_command())
    logger.log_message("Project Building Complete")
    


def cook_uproject() -> None:
    cook_commands = get_cook_project_commands()
    for command in cook_commands:
        # not using shell to make command max length more consistent
        run_proj_command(command, False)


def package_uproject_non_iostore() -> None:
    run_proj_command(get_engine_pak_command())


def run_proj_command(command: list[str], use_shell: bool = True) -> None:
    unreal_engine_dir = settings.get_unreal_engine_dir_or_raise()
    app_runner.run_app(
        exe_path=Path(command[0]),
        args=command[1:],
        working_dir=unreal_engine_dir,
        use_shell=use_shell,
    )


def handle_uninstall_logic() -> None:
    mods_info_dict = settings.get_mods_info_dict_from_json()
    for mod_name in settings.get_disabled_mod_names():
        uninstall_mod(mods_info_dict[mod_name]['packing_type'], mod_name)


@hook_states.hook_state_decorator(
    start_hook_state_type=HookStateType.PRE_PAK_DIR_SETUP,
    end_hook_state_type=HookStateType.POST_PAK_DIR_SETUP,
)
def handle_install_logic(*, use_symlinks: bool) -> None:
    mods_info_dict = settings.get_mods_info_dict_from_json()
    for mod_name in settings.get_enabled_mod_names():
        mod_info = mods_info_dict[mod_name]
        packing_type = data_structures.get_enum_from_val(PackingType, mod_info['packing_type'])
        if packing_type == PackingType.RETOC:
            install_mod(
                packing_type=packing_type,
                mod_name=mod_name,
                compression_type=None,
                use_symlinks=use_symlinks,
            )
        elif packing_type == PackingType.REPAK:
            install_mod(
                packing_type=packing_type,
                mod_name=mod_name,
                compression_type=None,
                use_symlinks=use_symlinks,
            )
        elif packing_type == PackingType.LOOSE:
            install_mod(
                packing_type=packing_type,
                mod_name=mod_name,
                compression_type=None,
                use_symlinks=use_symlinks,
            )
        else:
            test = mod_info.get("compression_type", None)
            if test:
                install_mod(
                    packing_type=packing_type,
                    mod_name=mod_name,
                    compression_type=CompressionType(
                        get_enum_from_val(
                            CompressionType, mod_info.get("compression_type", None),
                        ),
                    ),
                    use_symlinks=use_symlinks,
                )
            else:
                install_mod(
                    packing_type=packing_type,
                    mod_name=mod_name,
                    compression_type=None,
                    use_symlinks=use_symlinks,
                )


@hook_states.hook_state_decorator(
    start_hook_state_type=HookStateType.PRE_MODS_UNINSTALL,
    end_hook_state_type=HookStateType.POST_MODS_UNINSTALL,
)
def mods_uninstall() -> None:
    handle_uninstall_logic()


@hook_states.hook_state_decorator(
    start_hook_state_type=HookStateType.PRE_MODS_INSTALL,
    end_hook_state_type=HookStateType.POST_MODS_INSTALL,
)
def mods_install(*, use_symlinks: bool) -> None:
    handle_install_logic(use_symlinks=use_symlinks)


def generate_mods(*, use_symlinks: bool) -> None:
    mods_uninstall()
    mods_install(use_symlinks=use_symlinks)

    for command in command_queue:
        app_runner.run_app(command)


def uninstall_loose_mod(mod_name: str) -> None:
    mod_files = get_mod_paths_for_loose_mods(mod_name)
    dict_keys = mod_files.keys()
    for key in dict_keys:
        file_to_remove = mod_files[key]
        if file_to_remove.is_file():
            file_to_remove.unlink()
        if file_to_remove.is_symlink():
            file_to_remove.unlink()

    for folder in {file.parent for file in mod_files.values()}:
        if folder.exists() and not folder.iterdir():
            os.removedirs(folder)


def uninstall_pak_mod(mod_name: str) -> None:
    uproject_file = settings.get_uproject_file_or_raise()
    custom_game_dir = utilities.get_game_dir_or_raise()
    extensions = unreal_engine.get_game_pak_folder_archives(
        uproject_file, custom_game_dir,
    )
    if unreal_engine.is_game_ue5(settings.get_unreal_engine_dir()):
        extensions.extend(["ucas", "utoc"])
    for extension in extensions:
        base_path = Path(utilities.get_game_paks_dir() / utilities.get_pak_dir_structure(mod_name))
        file_path = Path(base_path / f"{mod_name}.{extension}")
        sig_path = Path(base_path / f"{mod_name}.sig")
        if file_path.is_file():
            file_path.unlink()
        if file_path.is_symlink():
            file_path.unlink()
        if sig_path.is_file():
            sig_path.unlink()
        if sig_path.is_symlink():
            sig_path.unlink()


def uninstall_mod(packing_type: PackingType, mod_name: str) -> None:
    if packing_type == PackingType.LOOSE:
        uninstall_loose_mod(mod_name)
    elif packing_type in list(PackingType):
        uninstall_pak_mod(mod_name)


def install_mod_sig(mod_name: str, *, use_symlinks: bool) -> None:
    game_paks_dir = utilities.get_game_paks_dir()
    pak_dir_str = utilities.get_pak_dir_structure(mod_name)
    sig_method_type = data_structures.get_enum_from_val(
        data_structures.SigMethodType,
        utilities.get_mod_info_from_mod_name(mod_name).get(
            "sig_method_type", "none",
        ),
    )
    sig_location = Path(f"{game_paks_dir}/{pak_dir_str}/{mod_name}.sig")
    if sig_location.is_file():
        sig_location.unlink()
    sig_location.parent.mkdir(parents=True, exist_ok=True)
    if sig_method_type in data_structures.SigMethodType:
        if sig_method_type == data_structures.SigMethodType.COPY:
            sig_files = file_io.filter_by_extension(
                file_io.get_files_in_dir(game_paks_dir), ".sig",
            )
            if len(sig_files) < 1:
                no_sigs_found = ""
                raise RuntimeError(no_sigs_found)
            src_sig_file = Path(f"{game_paks_dir}/{sig_files[0]}")
            if use_symlinks:
                src_sig_file.symlink_to(sig_location)
            else:
                shutil.copy(src_sig_file, sig_location)
        if sig_method_type == data_structures.SigMethodType.EMPTY:
            if use_symlinks:
                other_sig_location =  Path(
                    f"{settings.get_temp_directory()}/sig_files/{mod_name}.sig",
                )
                other_sig_location.parent.mkdir(parents=True, exist_ok=True)
                with other_sig_location.open("w"):
                    pass
                other_sig_location.symlink_to(sig_location)
            else:
                with sig_location.open("w"):
                    pass
    else:
        logger.log_message(
            f"Error: You have provided an invalid sig method type in your mod entry for the {mod_name} mod.",
        )
        logger.log_message("Error: Valid options are:")
        for enum in data_structures.get_enum_strings_from_enum(
            data_structures.SigMethodType,
        ):
            logger.log_message(
                f"Error: {data_structures.get_enum_from_val(data_structures.SigMethodType, enum)}",
            )
        raise RuntimeError


def install_loose_mod(mod_name: str, *, use_symlinks: bool) -> None:
    mod_files = get_mod_paths_for_loose_mods(mod_name)
    dict_keys = mod_files.keys()
    for key in dict_keys:
        src_file = key
        dest_file = mod_files[key]
        dest_file.parent.mkdir(parents=True, exist_ok=True)
        if src_file.exists():
            if dest_file.is_symlink():
                dest_file.unlink()
            if dest_file.is_file():
                dest_file.unlink()
        if src_file.is_file():
            if use_symlinks:
                src_file.symlink_to(dest_file)
            else:
                shutil.copyfile(src_file, dest_file)


def install_engine_mod(mod_name: str, *, use_symlinks: bool) -> None:
    mod_files = []
    pak_chunk_num = utilities.get_mod_info_from_mod_name(mod_name)[
        "pak_chunk_num"
    ]
    uproject_file = settings.get_uproject_file_or_raise()
    uproject_dir = unreal_engine.get_uproject_dir(uproject_file)
    win_dir_str = unreal_engine.get_win_dir_str(settings.get_unreal_engine_dir())
    uproject_name = unreal_engine.get_uproject_name(uproject_file)
    prefix = f"{uproject_dir}/Saved/StagedBuilds/{win_dir_str}/{uproject_name}/Content/Paks/pakchunk{pak_chunk_num}-{win_dir_str}."
    mod_files.append(prefix)
    custom_game_dir = utilities.get_game_dir_or_raise()
    for file in mod_files:
        for suffix in unreal_engine.get_game_pak_folder_archives(
            uproject_file, custom_game_dir,
        ):
            dir_engine_mod = Path(f"{custom_game_dir}/Content/Paks/{utilities.get_pak_dir_structure(mod_name)}")
            dir_engine_mod.mkdir(exist_ok=True)
            src_file = Path(f"{file}{suffix}")
            if not src_file.is_file():
                error_message = "Error: The engine did not generate a pak and/or ucas/utoc for your specified chunk id, this indicates an engine, project, or settings.json configuration issue."
                logger.log_message(error_message)
                raise FileNotFoundError(error_message)
            dest_file = Path(f"{dir_engine_mod}/{mod_name}.{suffix}")
            if dest_file.is_symlink():
                dest_file.unlink()
            if dest_file.is_file():
                dest_file.unlink()
            install_mod_sig(mod_name, use_symlinks=use_symlinks)
            if use_symlinks:
                src_file.symlink_to(dest_file)
            else:
                shutil.copyfile(src_file, dest_file)


def make_pak_repak(*, mod_name: str, use_symlinks: bool) -> None:
    game_paks_dir = utilities.get_game_paks_dir()
    pak_dir_structure = utilities.get_pak_dir_structure(mod_name)
    pak_dir = Path(f"{game_paks_dir}/{pak_dir_structure}")
    pak_dir.mkdir(exist_ok=True)
    os.chdir(pak_dir)

    src_symlinked_dir = Path(f"{settings.get_temp_directory()}/{mod_name}")

    if not src_symlinked_dir.is_dir() or not src_symlinked_dir.iterdir():
        logger.log_message(f"Error: {src_symlinked_dir}")
        logger.log_message(
            "Error: does not exist or is empty, indicating a packaging and/or config issue",
        )
        raise FileNotFoundError

    intermediate_pak_dir = (Path(f"{settings.get_temp_directory()}/{utilities.get_pak_dir_structure(mod_name)}"))
    intermediate_pak_dir.mkdir(exist_ok=True)
    intermediate_pak_file = Path(f"{intermediate_pak_dir}/{mod_name}.pak")

    dest_pak_location = Path(f"{pak_dir}/{mod_name}.pak")
    if dest_pak_location.is_symlink():
        dest_pak_location.unlink()
    if dest_pak_location.is_file():
        dest_pak_location.unlink()

    repak.run_repak_pack_command(src_symlinked_dir, intermediate_pak_file)

    install_mod_sig(mod_name, use_symlinks=use_symlinks)
    if use_symlinks:
        intermediate_pak_file.symlink_to(dest_pak_location)
    else:
        shutil.copyfile(intermediate_pak_file, dest_pak_location)


def install_repak_mod(mod_name: str, *, use_symlinks: bool) -> None:
    should_use_progress_bars = settings.should_show_progress_bars()
    mod_files_dict = get_mod_file_paths_for_manually_made_pak_mods(mod_name)
    mod_files_dict = utilities.filter_file_paths(mod_files_dict)

    def copy_files() -> None:
        for src_file, dest_file in mod_files_dict.items():
            dest_dir = dest_file.parent
            if dest_file.exists():
                dest_file.unlink()
            if not dest_dir.is_dir():
                dest_dir.mkdir(parents=True)
            if src_file.is_file():
                shutil.copy2(src_file, dest_file)

    if should_use_progress_bars:
        with Progress() as progress:
            task = progress.add_task(
                f"[green]Copying files for {mod_name} mod...", total=len(mod_files_dict),
            )
            for src_file, dest_file in mod_files_dict.items():
                dest_dir = dest_file.parent
                if dest_file.exists():
                    dest_file.unlink()
                if not dest_dir.is_dir():
                    dest_dir.mkdir(parents=True)
                if src_file.is_file():
                    shutil.copy2(src_file, dest_file)
                progress.update(task, advance=1)
    else:
        copy_files()

    make_pak_repak(mod_name=mod_name, use_symlinks=use_symlinks)


def install_mod(
    *,
    packing_type: PackingType,
    mod_name: str,
    compression_type: CompressionType | None,
    use_symlinks: bool,
) -> None:
    if packing_type == PackingType.LOOSE:
        install_loose_mod(mod_name, use_symlinks=use_symlinks)
    elif packing_type == PackingType.ENGINE:
        install_engine_mod(mod_name, use_symlinks=use_symlinks)
    elif packing_type == PackingType.REPAK:
        install_repak_mod(mod_name, use_symlinks=use_symlinks)
    elif packing_type == PackingType.UNREAL_PAK:
        unreal_pak.install_unreal_pak_mod(
            mod_name, compression_type, use_symlinks=use_symlinks,
        )
    elif packing_type == PackingType.RETOC:
        retoc.install_retoc_mod(mod_name=mod_name, use_symlinks=use_symlinks)
    else:
        logger.log_message(
            f'Error: You have provided an invalid packing_type for your "{mod_name}" mod entry in your settings json',
        )
        logger.log_message(
            f'Error: You provided "{utilities.get_mods_info_dict_from_mod_name(mod_name).get("packing_type", "none")}".',
        )
        logger.log_message("Error: Valid packing type options are:")
        for entry in PackingType:
            logger.log_message(f'Error: "{entry.value}"')
        invalid_packing_type_error = (
            "Invalid packing type, or no packing type, provided for mod entry"
        )
        raise RuntimeError(invalid_packing_type_error)



def contains_source_dir(root: Path) -> bool:
    root = Path(root)
    return any(p.name == "Source" for p in root.rglob("*") if p.is_dir())


def package_project_iostore() -> None:
    if unreal_engine.is_game_ue4(settings.get_unreal_engine_dir()):
        package_project_iostore_ue4()
    else:
        package_project_iostore_ue5()


def package_project_iostore_ue4() -> None:
    unreal_engine_dir = settings.get_unreal_engine_dir_or_raise()
    uproject_path = settings.get_uproject_file_or_raise()
    editor_cmd_exe_path = unreal_engine.get_editor_cmd_path(
        unreal_engine_dir,
    )
    archive_directory = f"{settings.get_temp_directory()}/iostore_packaging/output"
    args = [
        f'-ScriptsForProject="{uproject_path}"',
        "BuildCookRun",
        "-nocompileeditor",
        "-installed",
        "-nop4",
        f'-project="{uproject_path}"',
        "-archive",
        f'-archivedirectory="{archive_directory}"',
        f"-ue4exe={editor_cmd_exe_path}",
        "-ddc=InstalledDerivedDataBackendGraph",
        "-iostore",
        "-pak",
        "-stage",
        "-cook",
        # "-skipstage",
        # "-cookonthefly",
        "-iostore",
        "-prereqs",
        "-nodebuginfo",
        "-manifests",
        f"-targetplatform={settings.get_build_target_platform()}",
        f'-clientconfig="{settings.get_build_configuration_state()}"',
        "-utf8output",
        "-iterate",
    ]
    uproject_dir = uproject_path.parent
    if not unreal_engine.get_build_target_file_path(uproject_path).is_file():
        if contains_source_dir(uproject_dir):
            args.append('-build')
    app_runner.run_app(
        exe_path=unreal_engine.get_run_uat_script_path(),
        args=args,
        working_dir=unreal_engine_dir,
    )


def package_project_iostore_ue5() -> None:
    # add an option here for -legacyiterative instead of -cookincremental later
    unreal_engine_dir = settings.get_unreal_engine_dir_or_raise()
    uproject_path = settings.get_uproject_file_or_raise()
    editor_cmd_exe_path = unreal_engine.get_editor_cmd_path(unreal_engine_dir)
    archive_directory = Path(f"{settings.get_temp_directory()}/iostore_packaging/output")
    args = [
        f'-ScriptsForProject="{uproject_path}"',
        "BuildCookRun",
        "-nocompileeditor",
        "-installed",
        "-nop4",
        f'-project="{uproject_path}"',
        "-archive",
        f'-archivedirectory="{archive_directory}"',
        f"-unrealexe={editor_cmd_exe_path}",
        "-ddc=InstalledDerivedDataBackendGraph",
        "-iostore",
        "-pak",
        "-stage",
        "-cook",
        # "-skipstage",
        # "-cookonthefly",
        "-iostore",
        "-prereqs",
        "-nodebuginfo",
        "-manifests",
        f"-targetplatform={settings.get_build_target_platform()}",
        f'-clientconfig="{settings.get_build_configuration_state()}"',
        "-utf8output",
        "-cookincremental",
    ]
    uproject_dir = uproject_path.parent
    if not unreal_engine.get_build_target_file_path(uproject_path).is_file():
        if contains_source_dir(uproject_dir):
            args.append('-build')
    app_runner.run_app(
        exe_path=unreal_engine.get_run_uat_script_path(),
        args=args,
        working_dir=unreal_engine_dir,
    )


def get_debug_engine_building_args() -> list:
    return [
        "-build",
        "-skipstage",
        "-nodebuginfo",
        "-noP4",
        f"-targetplatform={settings.get_build_target_platform()}",
        '-clientconfig=Debug',
    ]


# for if you are just repacking an ini for an iostore game and don't need a ucas or utoc for example
# actually implement this later on
def does_iostore_game_need_utoc_ucas() -> bool:
    # needs_more_than_pak = True
    # return needs_more_than_pak
    return True


def get_debug_build_project_command() -> list[str]:
    command = [
        f'"{unreal_engine.get_run_uat_script_path()}"',
        'BuildCookRun',
        f'-project="{settings.get_uproject_file_or_raise()}"',
    ]
    for arg in get_debug_engine_building_args():
        command.append(arg)
    return command


def build_editor_target() -> None:
    run_proj_command(get_debug_build_project_command()) # Can it use the new build system instead?


@hook_states.hook_state_decorator(
    start_hook_state_type=HookStateType.PRE_COOKING,
    end_hook_state_type=HookStateType.POST_COOKING,
)
def build_cook() -> None:
    # the below uses a build command that is slower, user the newer method, don't check the build target path, command that out and just run it
    uproject_file = settings.get_uproject_file_or_raise()
    game_dir = utilities.get_game_dir_or_raise()
    is_game_iostore = unreal_engine.get_is_game_iostore(uproject_file, game_dir)
    needs_engine_command_run = PackingType.ENGINE in queue_information.install_queue_types
    does_iostore_needs_all_three_files = does_iostore_game_need_utoc_ucas()

    if needs_engine_command_run and does_iostore_needs_all_three_files and is_game_iostore:
        build_editor_target()
        build_uproject()
        cook_uproject()
        package_project_iostore()
    if needs_engine_command_run and not does_iostore_needs_all_three_files and is_game_iostore:
        build_uproject()
        cook_uproject()
        package_uproject_non_iostore()
    if not is_game_iostore and needs_engine_command_run:
        # maybe should still cook uproject here? for now yes, the manual specified ones may not cook but be expected, they souldn't recook twice usually nless args are changed to not iterate maybe
        build_uproject()
        cook_uproject()
        package_uproject_non_iostore()
    if not is_game_iostore and not needs_engine_command_run:
        build_editor_target() # didn't seem to always need this but now do?
        build_uproject()
        cook_uproject()



def get_mod_files_asset_paths_for_loose_mods(mod_name: str) -> dict[Path, Path]:
    file_dict = {}
    unreal_engine_dir = settings.get_unreal_engine_dir_or_raise()
    uproject_file = settings.get_uproject_file_or_raise()
    cooked_uproject_dir = unreal_engine.get_cooked_uproject_dir(
        uproject_file, unreal_engine_dir,
    )
    game_dir = utilities.get_game_dir_or_raise()
    mod_info = get_mod_pak_entry(mod_name)
    for asset in mod_info.get("file_includes", {}).get("asset_paths", []):
        base_path = f"{cooked_uproject_dir}/{asset}"
        for extension in file_io.get_file_extensions(base_path):
            src_file = Path(f"{base_path}{extension}")
            dest_file = Path(f"{game_dir}/{asset}{extension}")
            file_dict[src_file] = dest_file
    return file_dict


def get_mod_files_tree_paths_for_loose_mods(mod_name: str) -> dict[Path, Path]:
    file_dict = {}
    unreal_engine_dir = settings.get_unreal_engine_dir_or_raise()
    uproject_file = settings.get_uproject_file_or_raise()
    cooked_uproject_dir = unreal_engine.get_cooked_uproject_dir(
        uproject_file, unreal_engine_dir,
    )
    game_dir = utilities.get_game_dir_or_raise()
    mod_info = get_mod_pak_entry(mod_name)
    for tree in mod_info.get("file_includes", {}).get("tree_paths", []):
        tree_path = Path(f"{cooked_uproject_dir}/{tree}")
        for entry in file_io.get_files_in_tree(tree_path):
            if entry.is_file():
                base_entry = entry.stem
                for extension in file_io.get_file_extensions(str(entry)):
                    src_file = Path(f"{base_entry}{extension}")
                    relative_path = os.path.relpath(base_entry, cooked_uproject_dir)
                    dest_file = Path(f"{game_dir}/{relative_path}{extension}")
                    file_dict[src_file] = dest_file
    return file_dict


def get_mod_files_persistent_paths_for_loose_mods(mod_name: str) -> dict[Path, Path]:
    file_dict = {}
    persistent_mod_dir = settings.get_persistent_mod_dir(mod_name)
    game_dir = utilities.get_game_dir_or_raise()
    for root, _, files in persistent_mod_dir.walk():
        for file in files:
            file_path = Path(root / file)
            relative_path = os.path.relpath(file_path, persistent_mod_dir)
            game_dir_path = Path(game_dir / relative_path)
            file_dict[file_path] = game_dir_path
    return file_dict


def get_mod_files_mod_name_dir_paths_for_loose_mods(mod_name: str) -> dict[Path, Path]:
    file_dict = {}
    unreal_engine_dir = settings.get_unreal_engine_dir_or_raise()
    uproject_file = settings.get_uproject_file_or_raise()
    cooked_game_name_mod_dir = f"{unreal_engine.get_cooked_uproject_dir(uproject_file, unreal_engine_dir)}/Content/{utilities.get_unreal_mod_tree_type_str(mod_name)}/{utilities.get_mod_name_dir_name(mod_name)}"
    cooked_game_name_mod_dir = Path(cooked_game_name_mod_dir)
    game_dir = utilities.get_game_dir_or_raise()
    for file in file_io.get_files_in_tree(cooked_game_name_mod_dir):
        relative_file_path = os.path.relpath(file, cooked_game_name_mod_dir)
        src_path = Path(f"{cooked_game_name_mod_dir}/{relative_file_path}")
        dest_path = Path(f"{game_dir}/Content/{utilities.get_unreal_mod_tree_type_str(mod_name)}/{utilities.get_mod_name_dir_name(mod_name)}/{relative_file_path}")
        file_dict[src_path] = dest_path
    return file_dict


def get_mod_paths_for_loose_mods(mod_name: str) -> dict[Path, Path]:
    file_dict = {}
    file_dict.update(get_mod_files_asset_paths_for_loose_mods(mod_name))
    file_dict.update(get_mod_files_tree_paths_for_loose_mods(mod_name))
    file_dict.update(get_mod_files_persistent_paths_for_loose_mods(mod_name))
    file_dict.update(get_mod_files_mod_name_dir_paths_for_loose_mods(mod_name))

    return file_dict


def get_cooked_mod_file_paths(mod_name: str) -> list:
    return list((get_mod_paths_for_loose_mods(mod_name)).keys())


def get_game_mod_file_paths(mod_name: str) -> list:
    return list((get_mod_paths_for_loose_mods(mod_name)).values())


def get_mod_file_paths_for_manually_made_pak_mods_asset_paths(mod_name: str) -> dict[Path, Path]:
    file_dict = {}
    unreal_engine_dir = settings.get_unreal_engine_dir_or_raise()
    uproject_file = settings.get_uproject_file_or_raise()
    cooked_uproject_dir = unreal_engine.get_cooked_uproject_dir(
        uproject_file, unreal_engine_dir,
    )
    mod_info = get_mod_pak_entry(mod_name)
    for asset in mod_info.get("file_includes", {}).get("asset_paths", []):
        base_path = f"{cooked_uproject_dir}/{asset}"
        for extension in file_io.get_file_extensions(base_path):
            src_path = Path(f"{base_path}{extension}")
            dest_path = Path(f"{settings.get_temp_directory()}/{mod_name}/{unreal_engine.get_uproject_name(uproject_file)}/{asset}{extension}")
            file_dict[src_path] = dest_path
    return file_dict


def get_mod_file_paths_for_manually_made_pak_mods_tree_paths(mod_name: str) -> dict[Path, Path]:
    file_dict = {}
    unreal_engine_dir = settings.get_unreal_engine_dir_or_raise()
    uproject_file = settings.get_uproject_file_or_raise()
    cooked_uproject_dir = unreal_engine.get_cooked_uproject_dir(
        uproject_file, unreal_engine_dir,
    )
    mod_info = get_mod_pak_entry(mod_name)
    for tree in mod_info.get("file_includes", {}).get("tree_paths", []):
        tree_path = Path(f"{cooked_uproject_dir}/{tree}")
        for entry in file_io.get_files_in_tree(tree_path):
            if entry.is_file():
                base_entry = entry.with_suffix('')
                for extension in file_io.get_file_extensions(str(base_entry)):
                    src_path = Path(f"{base_entry}{extension}")
                    relative_path = os.path.relpath(base_entry, cooked_uproject_dir)
                    dest_path = Path(f"{settings.get_temp_directory()}/{mod_name}/{unreal_engine.get_uproject_name(uproject_file)}/{relative_path}{extension}")
                    file_dict[src_path] = dest_path
    return file_dict


def get_mod_file_paths_for_manually_made_pak_mods_persistent_paths(
    mod_name: str,
) -> dict[Path, Path]:
    file_dict = {}
    persistent_mod_dir = settings.get_persistent_mod_dir(mod_name)

    for root, _, files in persistent_mod_dir.walk():
        for file in files:
            file_path = Path(root / file)
            relative_path = os.path.relpath(file_path, persistent_mod_dir)
            # FIXME
            game_dir = settings.get_temp_directory().parent # why is there here but not in use?
            game_dir_path = Path(f"{settings.get_temp_directory()}/{mod_name}/{relative_path}")
            file_dict[file_path] = game_dir_path
    return file_dict


def get_mod_file_paths_for_manually_made_pak_mods_mod_name_dir_paths(
    mod_name: str,
) -> dict:
    file_dict = {}

    uproject_path = settings.get_uproject_file_or_raise()

    unreal_engine_dir = settings.get_unreal_engine_dir_or_raise()

    # the below line is returning incorrectly for some reason
    cooked_uproject_dir = unreal_engine.get_cooked_uproject_dir(uproject_path, unreal_engine_dir)

    cooked_game_name_mod_dir = Path(f"{cooked_uproject_dir}/Content/{utilities.get_unreal_mod_tree_type_str(mod_name)}/{utilities.get_mod_name_dir_name(mod_name)}")

    for file in file_io.get_files_in_tree(cooked_game_name_mod_dir):
        relative_file_path = os.path.relpath(file, cooked_game_name_mod_dir)
        src_path = Path(f"{cooked_game_name_mod_dir}/{relative_file_path}")
        potential_alt_dir_name = settings.get_alt_packing_dir_name()
        if potential_alt_dir_name:
            dir_name = potential_alt_dir_name
        else:
            dir_name = unreal_engine.get_uproject_name(uproject_path)
        dest_path = Path(f"{settings.get_temp_directory()}/{mod_name}/{dir_name}/Content/{utilities.get_unreal_mod_tree_type_str(mod_name)}/{utilities.get_mod_name_dir_name(mod_name)}/{relative_file_path}")
        file_dict[src_path] = dest_path
    return file_dict


def get_mod_file_paths_for_manually_made_pak_mods(mod_name: str) -> dict[Path, Path]:
    file_dict: dict[Path, Path] = {}
    file_dict.update(
        get_mod_file_paths_for_manually_made_pak_mods_asset_paths(mod_name),
    )
    file_dict.update(get_mod_file_paths_for_manually_made_pak_mods_tree_paths(mod_name))
    file_dict.update(
        get_mod_file_paths_for_manually_made_pak_mods_persistent_paths(mod_name),
    )
    file_dict.update(
        get_mod_file_paths_for_manually_made_pak_mods_mod_name_dir_paths(mod_name),
    )

    return file_dict
