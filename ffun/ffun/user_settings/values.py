from ffun.core.register import Entity, Register

from .types import Type


class Value(Entity):
    def __init__(
        self, key: int, name: str, type: Type, default: str | int | bool | None, description: str | None
    ) -> None:
        super().__init__(key=key)
        self.name = name
        self.type = type
        self.default = default
        self.description = description


user_settings: Register[Value] = Register()
