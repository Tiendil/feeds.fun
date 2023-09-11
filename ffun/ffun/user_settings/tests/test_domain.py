import asyncio
import enum
import random
import uuid

import pytest

from ffun.core import utils
from ffun.core.register import Entity, Register
from ffun.user_settings import domain, errors, operations, types
from ffun.user_settings.tests import asserts
from ffun.user_settings.values import SettingsRegister, Value, user_settings

_kind_1 = 1234
_kind_2 = 5678


class Setting(enum.IntEnum):
    kind_integer = 1
    kind_string = 2
    kind_boolean = 3
    kind_secret = 4


_integer_default = 123
_string_default = "abc"
_boolean_default = True
_secret_default = "secret"


register: SettingsRegister = Register()


register.add(
    Value(
        key=Setting.kind_integer,
        name="integer",
        type=types.Integer(),
        default=_integer_default,
        description=""
    )
)

register.add(
    Value(
        key=Setting.kind_string,
        name="string",
        type=types.String(),
        default="",
        description=""
    )
)

register.add(
    Value(
        key=Setting.kind_boolean,
        name="boolean",
        type=types.Boolean(),
        default=_boolean_default,
        description=""
    )
)

register.add(
    Value(
        key=Setting.kind_secret,
        name="secret",
        type=types.Secret(),
        default=_secret_default,
        description=""
    )
)


class TestSave:

    @pytest.mark.asyncio
    async def test_save_with_conversion(self, internal_user_id: uuid.UUID) -> None:
        await domain.save_setting(internal_user_id, Setting.kind_integer, 124, register=register)
        await asserts.has_settings(internal_user_id, {Setting.kind_integer: "124"})

    @pytest.mark.asyncio
    async def test_do_not_save_after_error(self, internal_user_id: uuid.UUID) -> None:
        with pytest.raises(errors.WrongValueType):
            await domain.save_setting(internal_user_id, Setting.kind_integer, 'string instead of int', register=register)

        await asserts.has_no_settings(internal_user_id, {Setting.kind_integer})
