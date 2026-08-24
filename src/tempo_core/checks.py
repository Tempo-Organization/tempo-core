from tempo_core import settings


def atleast_one_enabled_mod_check() -> None:
    enabled_mods = settings.get_enabled_mod_names()
    if len(enabled_mods) == 0:
        raise RuntimeError('You are attempting to run an action for mods, when you have no enabled mods within your config.')
    