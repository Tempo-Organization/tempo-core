


def env_true(value: str | None) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def getenv(key, default=None) -> (str | None):
    import os
    return os.getenv(key=key, default=default)