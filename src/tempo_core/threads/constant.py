import threading
import time
from dataclasses import dataclass

from tempo_core import hook_states, logger
from tempo_core.data_structures import HookStateType


@dataclass
class ConstantThreadInformation:
    run_constant_thread: bool
    constant_thread: threading.Thread


constant_thread_information = ConstantThreadInformation(
    run_constant_thread=False,
    constant_thread=None,  # type: ignore
)


def constant_thread_runner(tick_rate: float = 0.01) -> None:
    while constant_thread_information.run_constant_thread:
        time.sleep(tick_rate)
        constant_thread_logic()


def constant_thread_logic() -> None:
    hook_states.hook_state_checks(HookStateType.CONSTANT)


def start_constant_thread() -> None:
    constant_thread_information.run_constant_thread = True
    constant_thread_information.constant_thread = threading.Thread(
        target=constant_thread_runner, daemon=True
    )
    constant_thread_information.constant_thread.start()


@hook_states.hook_state_decorator(HookStateType.POST_INIT)
def post_constant_thread_created_message() -> None:
    logger.log_message("Thread: Constant Thread Started")


def constant_thread() -> None:
    start_constant_thread()
    post_constant_thread_created_message()


def stop_constant_thread() -> None:
    constant_thread_information.run_constant_thread = False
    logger.log_message("Thread: Constant Thread Ended")
