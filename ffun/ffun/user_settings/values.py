import decimal

from ffun.core.register import Entity, Register
from ffun.user_settings.types import Type


class Value(Entity):
    def __init__(
        self,
        key: int,
        name: str,
        type: Type,
        default: str | int | bool | decimal.Decimal | None,
    ) -> None:
        super().__init__(key=key)
        self.name = name
        self.type = type
        self.default = default


SettingsRegister = Register[Value]


user_settings: SettingsRegister = Register()
