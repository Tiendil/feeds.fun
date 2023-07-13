
# TODO: rename this module, because mypy does not support name `types`
# TODO: refactor to use pydantic instead of custom types

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
        raise NotImplementedError('You must implement "serialize" method in child class')

    def deserialize(self, data: str) -> Any:
        raise NotImplementedError('You must implement "deserialize" method in child class')

    def normalize(self, value: Any) -> Any:
        raise NotImplementedError('You must implement "normalize" method in child class')


class Integer(Type):
    id = TypeId.integer

    def serialize(self, value: int) -> str:
        return str(value)

    def deserialize(self, data: str) -> int:
        return int(data)

    def normalize(self, value: Any) -> int:
        if value == '':
            return 0

        return int(value)


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
        return 'true' if value else 'false'

    def deserialize(self, data: str) -> bool:
        return data == 'true'

    def normalize(self, value: Any) -> bool:
        return value in (True, 'true', 'True')


class Secret(Type):
    id = TypeId.secret

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.fernet = Fernet(settings.secret_key)

    def serialize(self, value: str) -> str:
        return self.fernet.encrypt(value.encode()).decode()

    def deserialize(self, data: str) -> str:
        return self.fernet.decrypt(data.encode()).decode()

    def normalize(self, value: Any) -> str:
        return str(value)