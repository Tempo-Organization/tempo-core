import os
import sys
import shutil
import zipfile
import tarfile
import requests
from dataclasses import dataclass
from urllib.parse import urlparse

from tomlkit.toml_document import TOMLDocument
from tomlkit import table, document, dumps, loads
import platformdirs

from tempo_core import file_io, settings


@dataclass
class CacheEntry:
    release_tag: str
    installed_files: list[str]
    executable_path: str
    file_to_download: str
    download_url: str
    
    def is_cache_valid(self) -> bool:
        return all(os.path.isfile(file) for file in self.installed_files)


@dataclass
class Tool:
    tool_repo_url: str
    cache_entries: list[CacheEntry]

    def get_repo_author(self) -> str:
        path = urlparse(self.tool_repo_url).path.strip('/')
        return path.split('/')[0] if '/' in path else ''

    def get_repo_name(self) -> str:
        path = urlparse(self.tool_repo_url).path.strip('/')
        return path.split('/')[1] if '/' in path else ''
    
    def prune_tool(self, cache_directory: str):
        valid_files = set(os.path.abspath(f) for entry in self.cache_entries for f in entry.installed_files)

        for root, _, files in os.walk(cache_directory):
            for file in files:
                full_path = os.path.abspath(os.path.join(root, file))
                if full_path not in valid_files:
                    try:
                        os.remove(full_path)
                        print(f"[Pruned] {full_path}")
                    except Exception as e:
                        print(f"[Error] Could not remove {full_path}: {e}")


@dataclass
class Tools:
    tool_entries: list[Tool]
    
    def prune_all_tools(self, cache_root: str):
        for tool in self.tool_entries:
            repo_name = tool.get_repo_name()
            tool_cache_dir = os.path.join(cache_root, repo_name)
            if os.path.exists(tool_cache_dir):
                tool.prune_tool(tool_cache_dir)
    
    def prune_single_tool(self, tool_name: str, cache_root: str):
        for tool in self.tool_entries:
            if tool.get_repo_name() == tool_name:
                tool_cache_dir = os.path.join(cache_root, tool_name)
                if os.path.exists(tool_cache_dir):
                    tool.prune_tool(tool_cache_dir)
                else:
                    print(f"[Warning] Cache directory does not exist: {tool_cache_dir}")
                return
        print(f"[Warning] Tool '{tool_name}' not found in entries.")

    
    def prune_multiple_tools(self, tool_names: list[str], cache_root: str):
        for name in tool_names:
            self.prune_single_tool(name, cache_root)

    def to_toml_dict(self) -> dict:
            return {
                "tool_entries": [
                    {
                        "tool_repo_url": tool.tool_repo_url,
                        "cache_entries": [
                            {
                                "release_tag": entry.release_tag,
                                "installed_files": entry.installed_files,
                                "executable_path": entry.executable_path,
                                "download_url": entry.download_url,
                                "file_to_download": entry.file_to_download
                            } for entry in tool.cache_entries
                        ]
                    } for tool in self.tool_entries
                ]
            }

    @staticmethod
    def from_toml_dict(data: dict) -> 'Tools':
        tools = []
        for tool_data in data.get("tool_entries", []):
            entries = [
                CacheEntry(
                    release_tag=entry["release_tag"],
                    installed_files=entry["installed_files"],
                    executable_path=entry["executable_path"],
                    download_url=entry["download_url"],
                    file_to_download=entry["file_to_download"]
                )
                for entry in tool_data.get("cache_entries", [])
            ]
            tools.append(Tool(tool_repo_url=tool_data["tool_repo_url"], cache_entries=entries))
        return Tools(tool_entries=tools)
    

def list_tools(tools: Tools) -> None:
    print("Available tools in cache:")
    for tool in tools.tool_entries:
        print(f"- {tool.get_repo_name()} ({tool.tool_repo_url})")
        for entry in tool.cache_entries:
            print(f"  └─ version: {entry.release_tag}")


def prune_cache(tools: Tools, cache_root: str) -> None:
    print("Pruning entire cache...")
    tools.prune_all_tools(cache_root)
    print("Pruning complete.")


def uninstall_tool_from_cache(tools: Tools, tool_name: str, version_tag: str, cache_root: str) -> None:
    for tool in tools.tool_entries:
        if tool.get_repo_name() == tool_name:
            for entry in tool.cache_entries:
                if entry.release_tag == version_tag:
                    print(f"Uninstalling {tool_name} version {version_tag}...")
                    for file in entry.installed_files:
                        try:
                            os.remove(file)
                            print(f"  Removed: {file}")
                        except FileNotFoundError:
                            print(f"  Not found: {file}")
                    tool.cache_entries.remove(entry)
                    return
            print(f"[Warning] Version '{version_tag}' not found for '{tool_name}'.")
            return
    print(f"[Warning] Tool '{tool_name}' not found.")


def is_archive(filename: str) -> bool:
    return filename.endswith((
        '.zip',
        '.tar.gz',
        '.tgz',
        '.tar',
        '.tar.xz',
        '.txz',
    ))


def unpack_archive(archive_path: str, extract_to: str) -> list[str]:
    extracted_files = []

    if archive_path.endswith(".zip"):
        with zipfile.ZipFile(archive_path, 'r') as zip_ref:
            zip_ref.extractall(extract_to)
            extracted_files = [os.path.join(extract_to, f) for f in zip_ref.namelist()]

    elif archive_path.endswith((".tar.gz", ".tgz", ".tar", ".tar.xz", ".txz")):
        with tarfile.open(archive_path, 'r:*') as tar_ref:
            tar_ref.extractall(extract_to)
            extracted_files = [
                os.path.join(extract_to, member.name)
                for member in tar_ref.getmembers() if member.isfile()
            ]

    else:
        raise ValueError(f"Unsupported archive format: {archive_path}")

    return extracted_files


def get_tool_install_dir(tool_name: str, version_tag: str) -> str:
    if settings.is_windows():
        platform_name = 'windows'
    elif settings.is_linux():
        platform_name = 'linux'
    else:
        raise RuntimeError('You are on an unsupported os')
    return os.path.normpath(os.path.join(
        get_cache_dir(), "tools", tool_name, platform_name, version_tag
    ))


# currently does not store the data in the cache toml
def install_tool_to_cache(
        tools: Tools,
        tool_name: str,
        version_tag: str,
        file_paths: list[str],
        executable_path: str,
        file_to_download: str,
        download_url: str
    ) -> None:

    # Download if missing
    if not os.path.isfile(file_to_download):
        try:
            print(f"Downloading {download_url} to {file_to_download}...")
            response = requests.get(download_url, stream=True, timeout=15)
            response.raise_for_status()
            with open(file_to_download, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            print("  Download complete.")
        except Exception as e:
            print(f"[Error] Failed to download tool from {download_url}: {e}")
            return

    # Determine install directory
    install_dir = get_tool_install_dir(tool_name, version_tag)
    os.makedirs(install_dir, exist_ok=True)

    # Extract if needed
    unpacked_files = []
    if is_archive(file_to_download):
        unpacked_files = unpack_archive(file_to_download, install_dir)

        # this will need to check if the only thing in the zip root is a dir and unfolder it
        root_contents = os.listdir(install_dir)
        if len(root_contents) == 1:
            single_item = os.path.join(install_dir, root_contents[0])
            if os.path.isdir(single_item):
                print(f"  Flattening {single_item} into {install_dir}...")
                for item in os.listdir(single_item):
                    shutil.move(os.path.join(single_item, item), os.path.join(install_dir, item))
                shutil.rmtree(single_item)
                unpacked_files = [os.path.join(install_dir, f) for f in os.listdir(install_dir)]

        try:
            os.remove(file_to_download)
            print(f"  Removed archive: {file_to_download}")
        except Exception as e:
            print(f"[Error] Failed to remove archive: {e}")
    else:
        # Direct file, not archive — just move to install_dir
        for path in file_paths:
            dest = os.path.join(install_dir, os.path.basename(path))
            shutil.copy2(path, dest)
            unpacked_files.append(dest)

    # Register in cache
    for tool in tools.tool_entries:
        if tool.get_repo_name().lower() == tool_name.lower():
            print(f"Installing {tool_name} version {version_tag}...")
            entry = CacheEntry(
                release_tag=version_tag,
                installed_files=unpacked_files,
                executable_path=executable_path,
                file_to_download=file_to_download,
                download_url=download_url
            )
            tool.cache_entries.append(entry)
            print(f"  Installed to: {install_dir}")
            print(f"  Total files installed: {len(unpacked_files)}")
            return

    print(f"[Warning] Tool '{tool_name}' not found in tool list.")



def save_tools_to_toml_file(tools: Tools, filepath: str) -> None:
    doc = document()
    entries = []

    for tool in tools.tool_entries:
        tool_table = table()
        tool_table["tool_repo_url"] = tool.tool_repo_url

        cache_entries = []
        for entry in tool.cache_entries:
            entry_table = table()
            entry_table["release_tag"] = entry.release_tag
            entry_table["installed_files"] = entry.installed_files
            entry_table["download_url"] = entry.download_url
            entry_table["executable_path"] = entry.executable_path
            entry_table["file_to_download"] = entry.file_to_download
            cache_entries.append(entry_table)

        tool_table["cache_entries"] = cache_entries
        entries.append(tool_table)

    doc["tool_entries"] = entries

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(dumps(doc))

def load_tools_from_toml_file(filepath: str) -> Tools:
    with open(filepath, "r", encoding="utf-8") as f:
        data: TOMLDocument = loads(f.read())

    tool_entries = []
    for tool_data in data.get("tool_entries", []):
        cache_entries = [
            CacheEntry(
                release_tag=entry["release_tag"],
                installed_files=entry["installed_files"],
                executable_path=entry["executable_path"],
                download_url=entry["download_url"],
                file_to_download=entry["file_to_download"]
            )
            for entry in tool_data.get("cache_entries", [])
        ]
        tool = Tool(
            tool_repo_url=tool_data["tool_repo_url"],
            cache_entries=cache_entries
        )
        tool_entries.append(tool)

    return Tools(tool_entries=tool_entries)


def clean_cache():
    shutil.rmtree(get_cache_dir())
    init_cache()


def get_tempo_no_cache_env_var_value() -> bool:
    return os.getenv('TEMPO_NO_CACHE', '').lower() in ['1', 'true', 'yes']


def get_tempo_cache_dir_env_var_value() -> str | None:
    return os.getenv('TEMPO_CACHE_DIR')


def was_no_cache_parameter_in_args() -> bool:
    return '--no-cache' in sys.argv


def was_cache_dir_parameter_in_args() -> bool:
    return '--cache-dir' in sys.argv


def get_cache_dir_param_in_args() -> str | None:
    if '--cache-dir' in sys.argv:
        idx = sys.argv.index('--cache-dir')
        if idx + 1 < len(sys.argv):
            return sys.argv[idx + 1]
    return None


def get_default_cache_dir() -> str:
    return os.path.normpath(f"{platformdirs.user_cache_dir(appname='tempo', appauthor='Tempo-Organization')}")


def get_cache_dir_from_tempo_config_file() -> str | None:
    return settings.settings_information.settings.get("cache", {}).get("cache_dir", None)


def get_cache_dir() -> str:
    # check .env file here later for the value
    if get_tempo_no_cache_env_var_value() or was_no_cache_parameter_in_args():
        return get_local_cache_dir_path()

    if was_cache_dir_parameter_in_args():
        param_dir = get_cache_dir_param_in_args()
        if param_dir:
            return os.path.normpath(f"{param_dir}")

    env_dir = get_tempo_cache_dir_env_var_value()
    if env_dir:
        return os.path.normpath(f"{env_dir}")
    
    # check .env file here later for the value

    config_dir = get_cache_dir_from_tempo_config_file()
    if config_dir:
        return os.path.normpath(f"{config_dir}")

    return get_default_cache_dir()


def get_main_cache_settings_file() -> str:
    return os.path.normpath(f"{get_cache_dir()}/cache.toml")


def get_local_cache_dir_path() -> str:
    return os.path.normpath(f"{file_io.SCRIPT_DIR}/tempo_cache")


class _UninitializedCache:
    def __getattr__(self, name):
        raise NotImplementedError("ToolsCache is not initialized. Call init_cache() first.")

    def __getitem__(self, key):
        raise NotImplementedError("ToolsCache is not initialized. Call init_cache() first.")

    def __bool__(self):
        raise NotImplementedError("ToolsCache is not initialized. Call init_cache() first.")


TempoCache = _UninitializedCache()

def init_cache() -> None:
    cache_dir = get_cache_dir()
    print(f'cache_directory: "{get_cache_dir()}"')
    os.makedirs(cache_dir, exist_ok=True)
    cache = get_main_cache_settings_file()
    print(f'cache_settings_file: "{cache}"')
    if not os.path.isfile(cache):
        with open(cache, 'w') as file:
            file.write('')
    global TempoCache
    TempoCache = load_tools_from_toml_file(cache)
