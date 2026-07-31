

def env_true(value: str | None) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "on"}
