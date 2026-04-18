import threading
import time
from dataclasses import dataclass

import tempo_core.settings
from tempo_core import hook_states, logger, process_management, window_management
from tempo_core.data_structures import HookStateType
from tempo_core.programs import unreal_engine


@dataclass
class EngineMonitorThreadInformation:
    init_done: bool
    found_window: bool
    found_process: bool
    window_closed: bool
    run_engine_monitor_thread: bool
    engine_monitor_thread: threading.Thread


engine_monitor_thread_information = EngineMonitorThreadInformation(
    init_done=False,
    found_window=False,
    found_process=False,
    window_closed=False,
    run_engine_monitor_thread=False,
    engine_monitor_thread=None,  # type: ignore
)


def engine_monitor_thread() -> None:
    start_engine_monitor_thread()
    logger.log_message("Thread: Engine Monitoring Thread Started")
    engine_monitor_thread_information.engine_monitor_thread.join()
    logger.log_message("Thread: Engine Monitoring Thread Ended")


def engine_monitor_thread_runner(tick_rate: float = 0.01) -> None:
    while engine_monitor_thread_information.run_engine_monitor_thread:
        time.sleep(tick_rate)
        engine_monitor_thread_logic()


@hook_states.hook_state_decorator(HookStateType.POST_ENGINE_OPEN)
def found_engine_window() -> None:
    logger.log_message("Window: Engine Window Found")
    engine_monitor_thread_information.found_window = True


def engine_monitor_thread_logic() -> None:
    if not engine_monitor_thread_information.init_done:
        engine_monitor_thread_information.found_process = False
        engine_monitor_thread_information.found_window = False
        engine_monitor_thread_information.window_closed = False
        engine_monitor_thread_information.init_done = True

    engine_window_name = unreal_engine.get_engine_window_title(
        str(tempo_core.settings.get_uproject_file())
    )
    if not engine_monitor_thread_information.found_process:
        engine_process_name = unreal_engine.get_engine_process_name(
            str(tempo_core.settings.get_unreal_engine_dir())
        )
        if process_management.is_process_running(engine_process_name):
            logger.log_message("Process: Found Engine Process")
            engine_monitor_thread_information.found_process = True
    elif not engine_monitor_thread_information.found_window:
        if window_management.does_window_exist(engine_window_name):
            found_engine_window()
    elif not engine_monitor_thread_information.window_closed:
        if not window_management.does_window_exist(engine_window_name):
            logger.log_message("Window: Engine Window Closed")
            engine_monitor_thread_information.window_closed = True
            stop_engine_monitor_thread()


def start_engine_monitor_thread() -> None:
    engine_monitor_thread_information.run_engine_monitor_thread = True
    engine_monitor_thread_information.engine_monitor_thread = threading.Thread(
        target=engine_monitor_thread_runner, daemon=True
    )
    engine_monitor_thread_information.engine_monitor_thread.start()


@hook_states.hook_state_decorator(HookStateType.POST_ENGINE_CLOSE)
def stop_engine_monitor_thread() -> None:
    engine_monitor_thread_information.run_engine_monitor_thread = False
