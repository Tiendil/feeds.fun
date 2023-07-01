import enum
from typing import Any

from cryptography.fernet import Fernet

from .settings import settings


class TypeId(str, enum.Enum):
    integer = 'integer'
    string = 'string'
    boolean = 'boolean'
    secret = 'secret'


class Type:
    id = NotImplemented

    def serialize(self, value: Any) -> str:
        raise NotImplementedError()

    def deserialize(self, data: str) -> Any:
        raise NotImplementedError()


class Integer(Type):
    id = TypeId.integer

    def serialize(self, value: int) -> str:
        return str(value)

    def deserialize(self, data: str) -> int:
        return int(data)


class String(Type):
    id = TypeId.string

    def serialize(self, value: str) -> str:
        return value

    def deserialize(self, data: str) -> str:
        return data


class Boolean(Type):
    id = TypeId.boolean

    def serialize(self, value: bool) -> str:
        return 'true' if value else 'false'

    def deserialize(self, data: str) -> bool:
        return data == 'true'


class Secret(Type):
    id = TypeId.secret

    def __init__(self):
        self.fernet = Fernet(settings.secret_key)

    def serialize(self, value: str) -> str:
        return self.fernet.encrypt(value)

    def deserialize(self, data: str) -> str:
        return self.fernet.decrypt(data)
