import platform
import sys

def get_current_arch() -> str:
    return platform.machine() or platform.architecture()[0]

def get_current_os() -> str:
    return platform.system()
