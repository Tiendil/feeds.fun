import enum
from typing import Any, NewType


class TypeId(enum.StrEnum):
    integer = "integer"
    string = "string"
    boolean = "boolean"
    secret = "secret"  # noqa: S105
    decimal = "decimal"


SettingKind = NewType("SettingKind", int)

UserSettings = dict[SettingKind, Any]
