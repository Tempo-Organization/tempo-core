import os
import sys
from pathlib import Path

from tempo_core import file_io


def get_wrapper_location() -> Path:
    return Path(f"{file_io.SCRIPT_DIR}/dist/command.{file_io.get_platform_wrapper_extension()}")


def generate_wrapper() -> None:
    args = sys.argv[:]

    if "--wrapper_name" in args:
        index = args.index("--wrapper_name")
        args.pop(index)
        args.pop(index)

    if not Path(args[0]).is_absolute():
        args[0] = f'"{Path(file_io.SCRIPT_DIR / args[0])}"'

    content = " ".join(args)

    wrapper_path = get_wrapper_location()

    wrapper_path.parent.mkdir(parents=True, exist_ok=True)

    with wrapper_path.open("w") as f:
        f.write(content)
