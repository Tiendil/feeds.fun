import enum
import uuid
from typing import Any

import pytest

from ffun.core.register import Register
from ffun.user_settings import domain, errors, types
from ffun.user_settings.tests import asserts
from ffun.user_settings.values import SettingsRegister, Value

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
_secret_default = "secret"  # noqa: S105


register: SettingsRegister = Register()


register.add(
    Value(key=Setting.kind_integer, name="integer", type=types.Integer(), default=_integer_default, description="")
)

register.add(
    Value(key=Setting.kind_string, name="string", type=types.String(), default=_string_default, description="")
)

register.add(
    Value(key=Setting.kind_boolean, name="boolean", type=types.Boolean(), default=_boolean_default, description="")
)

register.add(
    Value(key=Setting.kind_secret, name="secret", type=types.Secret(), default=_secret_default, description="")
)


class TestSave:
    @pytest.mark.asyncio
    async def test_save_with_conversion(self, internal_user_id: uuid.UUID) -> None:
        await domain.save_setting(internal_user_id, Setting.kind_integer, 124, register=register)
        await asserts.has_settings(internal_user_id, {Setting.kind_integer: "124"})

    @pytest.mark.asyncio
    async def test_do_not_save_after_error(self, internal_user_id: uuid.UUID) -> None:
        with pytest.raises(errors.WrongValueType):
            await domain.save_setting(
                internal_user_id, Setting.kind_integer, "string instead of int", register=register
            )

        await asserts.has_no_settings(internal_user_id, {Setting.kind_integer})


class TestFullSettings:
    def test(self) -> None:
        values: dict[int, Any] = {Setting.kind_integer: "666", Setting.kind_boolean: "false"}

        settings = domain._full_settings(values, kinds=list(Setting), register=register)

        assert settings == {
            Setting.kind_integer: 666,
            Setting.kind_boolean: False,
            Setting.kind_string: _string_default,
            Setting.kind_secret: _secret_default,
        }


class TestLoadSettings:
    @pytest.mark.asyncio
    async def test_no_settings(self, internal_user_id: uuid.UUID) -> None:
        settings = await domain.load_settings(internal_user_id, kinds=list(Setting), register=register)

        assert settings == {
            Setting.kind_integer: _integer_default,
            Setting.kind_string: _string_default,
            Setting.kind_boolean: _boolean_default,
            Setting.kind_secret: _secret_default,
        }

    @pytest.mark.asyncio
    async def test_has_settings(self, internal_user_id: uuid.UUID, another_internal_user_id: uuid.UUID) -> None:
        await domain.save_setting(internal_user_id, Setting.kind_integer, 124, register=register)
        await domain.save_setting(internal_user_id, Setting.kind_string, "xxxyyy", register=register)
        await domain.save_setting(another_internal_user_id, Setting.kind_integer, 421, register=register)

        settings = await domain.load_settings(internal_user_id, kinds=list(Setting), register=register)
        assert settings == {
            Setting.kind_integer: 124,
            Setting.kind_string: "xxxyyy",
            Setting.kind_boolean: _boolean_default,
            Setting.kind_secret: _secret_default,
        }

        settings = await domain.load_settings(another_internal_user_id, kinds=list(Setting), register=register)
        assert settings == {
            Setting.kind_integer: 421,
            Setting.kind_string: _string_default,
            Setting.kind_boolean: _boolean_default,
            Setting.kind_secret: _secret_default,
        }

    @pytest.mark.asyncio
    async def test_filter_by_kinds(self, internal_user_id: uuid.UUID, another_internal_user_id: uuid.UUID) -> None:
        await domain.save_setting(internal_user_id, Setting.kind_integer, 124, register=register)
        await domain.save_setting(internal_user_id, Setting.kind_string, "xxxyyy", register=register)

        settings = await domain.load_settings(
            internal_user_id, kinds=[Setting.kind_integer, Setting.kind_secret], register=register
        )
        assert settings == {Setting.kind_integer: 124, Setting.kind_secret: _secret_default}


class TestLoadSettingsForUsers:
    @pytest.mark.asyncio
    async def test(self, internal_user_id: uuid.UUID, another_internal_user_id: uuid.UUID) -> None:
        await domain.save_setting(internal_user_id, Setting.kind_integer, 124, register=register)
        await domain.save_setting(internal_user_id, Setting.kind_string, "xxxyyy", register=register)
        await domain.save_setting(another_internal_user_id, Setting.kind_integer, 421, register=register)
        await domain.save_setting(another_internal_user_id, Setting.kind_secret, "my-secret", register=register)

        kinds = [Setting.kind_integer, Setting.kind_secret, Setting.kind_string]

        settings = await domain.load_settings(internal_user_id, kinds=kinds, register=register)
        assert settings == {
            Setting.kind_integer: 124,
            Setting.kind_string: "xxxyyy",
            Setting.kind_secret: _secret_default,
        }

        settings = await domain.load_settings(another_internal_user_id, kinds=kinds, register=register)
        assert settings == {
            Setting.kind_integer: 421,
            Setting.kind_string: _string_default,
            Setting.kind_secret: "my-secret",
        }


class TestGetUsersWithSetting:
    @pytest.mark.asyncio
    async def test_wrong_value(self) -> None:
        with pytest.raises(errors.WrongValueType):
            await domain.get_users_with_setting(Setting.kind_integer, "sdassd", register=register)

    @pytest.mark.asyncio
    async def test_no_users(self) -> None:
        value = uuid.uuid4().int
        user_ids = await domain.get_users_with_setting(Setting.kind_integer, value, register=register)
        assert user_ids == set()

    @pytest.mark.asyncio
    async def test_found_users(self, internal_user_id: uuid.UUID, another_internal_user_id: uuid.UUID) -> None:
        value = uuid.uuid4().hex

        await domain.save_setting(internal_user_id, Setting.kind_string, value, register=register)
        await domain.save_setting(another_internal_user_id, Setting.kind_string, uuid.uuid4().hex, register=register)

        user_ids = await domain.get_users_with_setting(Setting.kind_string, value, register=register)

        assert user_ids == {internal_user_id}

        await domain.save_setting(another_internal_user_id, Setting.kind_string, value, register=register)

        user_ids = await domain.get_users_with_setting(Setting.kind_string, value, register=register)

        assert user_ids == {internal_user_id, another_internal_user_id}
