import os
import socket

from tempo_core import logger, env

is_online = False
has_checked_online_status = False


def log_online_status() -> None:
    global has_checked_online_status
    if is_online:
        logger.log_message('Web Connectivity Status: Online')
    else:
        logger.log_message('Web Connectivity Status: Offline')
    has_checked_online_status = True


def init_is_online(timeout: float = 1) -> None:
    """
    Determine online status with the following priority:
    1. TEMPO_FORCE_ONLINE=true  -> always online
    2. TEMPO_FORCE_OFFLINE=true -> always offline
    3. Otherwise, attempt socket connection
    """
    global is_online

    force_online = env.env_true(os.getenv("TEMPO_FORCE_ONLINE"))
    force_offline = env.env_true(os.getenv("TEMPO_FORCE_OFFLINE"))

    if force_online:
        is_online = True
        log_online_status()
        return

    if force_offline:
        is_online = False
        log_online_status()
        return

    try:
        socket.create_connection(("8.8.8.8", 53), timeout=timeout)
        is_online = True
    except (socket.timeout, OSError):
        is_online = False

    log_online_status()
