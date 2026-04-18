import os
from typing import Protocol, TypeAlias


JSONValue: TypeAlias = (
    str | int | float | bool | None | list["JSONValue"] | dict[str, "JSONValue"]
)


def resolve_special_vars(value: JSONValue) -> JSONValue:
    special_vars: dict[str, str] = {
        "${workspaceFolder}": os.path.abspath(
            os.path.dirname(__file__)
        ),
        "${home}": os.path.expanduser("~"),
        "${cwd}": os.getcwd(),
    }

    if isinstance(value, str):
        for key, replacement in special_vars.items():
            value = value.replace(key, replacement)
    return value


class SupportsGetAndAttr(Protocol):
    def get(
        self, key: str, default: JSONValue | None = None
    ) -> JSONValue | None: ...
    def __getattr__(self, name: str) -> JSONValue: ...


class DynamicSettings:
    def __init__(self, settings: SupportsGetAndAttr) -> None:
        self._settings = settings

    def __getattr__(self, item: str) -> JSONValue:
        value = getattr(self._settings, item, None)
        return resolve_special_vars(value)

    def __getitem__(self, item: str) -> JSONValue | None:
        value = self._settings.get(item)
        return resolve_special_vars(value)
