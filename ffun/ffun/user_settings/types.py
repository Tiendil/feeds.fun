# TODO: rename this module, because mypy does not support name `types`
# TODO: refactor to use pydantic instead of custom types

import decimal
import enum

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

    def serialize(self, value: object) -> str:
        raise NotImplementedError('You must implement "serialize" method in child class')

    def deserialize(self, data: str) -> object:
        raise NotImplementedError('You must implement "deserialize" method in child class')

    def normalize(self, value: object) -> object:
        raise NotImplementedError('You must implement "normalize" method in child class')


class Integer(Type):
    id = TypeId.integer

    def serialize(self, value: object) -> str:
        if not isinstance(value, int):
            raise errors.WrongValueType(value=str(value))

        return str(value)

    def deserialize(self, data: str) -> int:
        return int(data)

    def normalize(self, value: object) -> int:
        if value == "":
            return 0

        return int(value)  # type: ignore


# TODO: test
class Decimal(Type):
    id = TypeId.decimal

    def serialize(self, value: object) -> str:
        if not isinstance(value, decimal.Decimal):
            raise errors.WrongValueType(value=str(value))

        return str(value)

    def deserialize(self, data: str) -> decimal.Decimal:
        return decimal.Decimal(data)

    def normalize(self, value: object) -> decimal.Decimal:
        if value == "":
            return decimal.Decimal(0)

        # Not the best place to apply normalization of such a kind
        # But for now, it is the simplest way to handle it
        # TODO: move decimal normalization to the frontend side, when the frontend is ready
        if isinstance(value, str):
            value = value.strip().replace(",", ".")

        return decimal.Decimal(value)  # type: ignore


class String(Type):
    id = TypeId.string

    def serialize(self, value: object) -> str:
        assert isinstance(value, str)
        return value

    def deserialize(self, data: str) -> str:
        return data

    def normalize(self, value: object) -> str:
        return str(value)


class Boolean(Type):
    id = TypeId.boolean

    def serialize(self, value: object) -> str:
        return "true" if value else "false"

    def deserialize(self, data: str) -> bool:
        return data == "true"

    def normalize(self, value: object) -> bool:
        return value in (True, "true", "True")


class Secret(Type):
    id = TypeId.secret

    def __init__(self, **kwargs: object) -> None:
        super().__init__(**kwargs)
        self.fernet = Fernet(settings.secret_key)

    def serialize(self, value: object) -> str:
        assert isinstance(value, str)
        return self.fernet.encrypt(value.encode()).decode()

    def deserialize(self, data: str) -> str:
        return self.fernet.decrypt(data.encode()).decode()

    def normalize(self, value: object) -> str:
        return str(value)
