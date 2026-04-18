import time

start_time = time.time()


def get_running_time() -> float:
    return time.time() - start_time
