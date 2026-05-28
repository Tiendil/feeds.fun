import enum
from typing import Any


class TypeId(str, enum.Enum):
    integer = "integer"
    string = "string"
    boolean = "boolean"
    secret = "secret"  # noqa: S105
    decimal = "decimal"


UserSettings = dict[int, Any]
