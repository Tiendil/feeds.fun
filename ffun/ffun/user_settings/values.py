
from ffun.core.register import Entity, Register

from .types import Type


class Value(Entity):

    def __init__(self, key: int, name: str, type: Type) -> None:
        super().__init__(key=key)
        self.name = name
        self.type = type


user_settings = Register()
