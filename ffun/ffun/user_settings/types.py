# TODO: rename this module, because mypy does not support name `types`
# TODO: refactor to use pydantic instead of custom types

import decimal
import enum
from typing import Any

from cryptography.fernet import Fernet

from ffun.user_settings import errors
from ffun.user_settings.settings import settings


class TypeId(str, enum.Enum):
    integer = "integer"
    string = "string"
    boolean = "boolean"
    secret = "secret"  # noqa: S105
    decimal = "decimal"


class Type:
    id: TypeId = NotImplemented

    def serialize(self, value: Any) -> str:
        raise NotImplementedError('You must implement "serialize" method in child class')

    def deserialize(self, data: str) -> Any:
        raise NotImplementedError('You must implement "deserialize" method in child class')

    def normalize(self, value: Any) -> Any:
        raise NotImplementedError('You must implement "normalize" method in child class')


class Integer(Type):
    id = TypeId.integer

    def serialize(self, value: int) -> str:
        if not isinstance(value, int):
            raise errors.WrongValueType(value=value)

        return str(value)

    def deserialize(self, data: str) -> int:
        return int(data)

    def normalize(self, value: Any) -> int:
        if value == "":
            return 0

        return int(value)


# TODO: test
class Decimal(Type):
    id = TypeId.decimal

    def serialize(self, value: decimal.Decimal) -> str:
        if not isinstance(value, decimal.Decimal):
            raise errors.WrongValueType(value=value)

        return str(value)

    def deserialize(self, data: str) -> decimal.Decimal:
        return decimal.Decimal(data)

    def normalize(self, value: Any) -> decimal.Decimal:
        if value == "":
            return decimal.Decimal(0)

        return decimal.Decimal(value)


class String(Type):
    id = TypeId.string

    def serialize(self, value: str) -> str:
        return value

    def deserialize(self, data: str) -> str:
        return data

    def normalize(self, value: Any) -> str:
        return str(value)


class Boolean(Type):
    id = TypeId.boolean

    def serialize(self, value: bool) -> str:
        return "true" if value else "false"

    def deserialize(self, data: str) -> bool:
        return data == "true"

    def normalize(self, value: Any) -> bool:
        return value in (True, "true", "True")


class Secret(Type):
    id = TypeId.secret

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.fernet = Fernet(settings.secret_key)

    def serialize(self, value: str) -> str:
        return self.fernet.encrypt(value.encode()).decode()

    def deserialize(self, data: str) -> str:
        return self.fernet.decrypt(data.encode()).decode()

    def normalize(self, value: Any) -> str:
        return str(value)
