import uuid

import pytest

from ffun.user_settings import operations
from ffun.user_settings.tests import asserts

_kind_1 = 1234
_kind_2 = 5678


class TestSave:
    @pytest.mark.asyncio
    async def test_save_load(self, internal_user_id: uuid.UUID) -> None:
        for value in ("abc", "def"):
            await operations.save_setting(internal_user_id, _kind_1, value)
            await asserts.has_settings(internal_user_id, {_kind_1: value})

    @pytest.mark.asyncio
    async def test_save_load_multiple_kinds(self, internal_user_id: uuid.UUID) -> None:
        await operations.save_setting(internal_user_id, _kind_1, "abc")
        await operations.save_setting(internal_user_id, _kind_2, "def")

        await asserts.has_settings(internal_user_id, {_kind_1: "abc", _kind_2: "def"})

    @pytest.mark.asyncio
    async def test_save_load_multiple_users(
        self, internal_user_id: uuid.UUID, another_internal_user_id: uuid.UUID
    ) -> None:
        await operations.save_setting(internal_user_id, _kind_1, "abc")
        await operations.save_setting(another_internal_user_id, _kind_1, "def")

        await asserts.has_settings(internal_user_id, {_kind_1: "abc"})
        await asserts.has_settings(another_internal_user_id, {_kind_1: "def"})


class TestLoadSettingsForUsers:
    @pytest.mark.asyncio
    async def test_no_users(self) -> None:
        assert await operations.load_settings_for_users([], [_kind_1]) == {}

    @pytest.mark.asyncio
    async def test_no_kinds(self, internal_user_id: uuid.UUID) -> None:
        assert await operations.load_settings_for_users([internal_user_id], []) == {internal_user_id: {}}

    @pytest.mark.asyncio
    async def test_no_settings_stored(self, internal_user_id: uuid.UUID, another_internal_user_id: uuid.UUID) -> None:
        settings = await operations.load_settings_for_users(
            [internal_user_id, another_internal_user_id], [_kind_1, _kind_2]
        )

        assert settings == {internal_user_id: {}, another_internal_user_id: {}}

    @pytest.mark.asyncio
    async def test_some_settings_stored(
        self, internal_user_id: uuid.UUID, another_internal_user_id: uuid.UUID
    ) -> None:
        await operations.save_setting(internal_user_id, _kind_1, "abc")
        await operations.save_setting(internal_user_id, _kind_2, "def")
        await operations.save_setting(another_internal_user_id, _kind_1, "ghi")

        settings = await operations.load_settings_for_users(
            [internal_user_id, another_internal_user_id], [_kind_1, _kind_2]
        )

        assert settings == {
            internal_user_id: {_kind_1: "abc", _kind_2: "def"},
            another_internal_user_id: {_kind_1: "ghi"},
        }


class TestGetUsersWithSetting:
    @pytest.mark.asyncio
    async def test_no_users(self) -> None:
        assert await operations.get_users_with_setting(_kind_1, uuid.uuid4().hex) == set()

    @pytest.mark.asyncio
    async def test_ignore_value_with_wrong_kind(
        self, internal_user_id: uuid.UUID, another_internal_user_id: uuid.UUID
    ) -> None:
        value_1 = uuid.uuid4().hex

        await operations.save_setting(internal_user_id, _kind_1, value_1)
        await operations.save_setting(another_internal_user_id, _kind_2, value_1)

        assert await operations.get_users_with_setting(_kind_1, value_1) == {internal_user_id}
        assert await operations.get_users_with_setting(_kind_2, value_1) == {another_internal_user_id}

    @pytest.mark.asyncio
    async def test_has_users(self, internal_user_id: uuid.UUID, another_internal_user_id: uuid.UUID) -> None:
        value_1 = uuid.uuid4().hex
        value_2 = uuid.uuid4().hex
        value_3 = uuid.uuid4().hex

        await operations.save_setting(internal_user_id, _kind_1, value_1)
        await operations.save_setting(another_internal_user_id, _kind_1, value_2)

        await operations.save_setting(internal_user_id, _kind_2, value_2)
        await operations.save_setting(another_internal_user_id, _kind_2, value_2)

        assert await operations.get_users_with_setting(_kind_1, value_1) == {internal_user_id}
        assert await operations.get_users_with_setting(_kind_1, value_2) == {another_internal_user_id}
        assert await operations.get_users_with_setting(_kind_1, value_3) == set()

        assert await operations.get_users_with_setting(_kind_2, value_1) == set()
        assert await operations.get_users_with_setting(_kind_2, value_2) == {
            internal_user_id,
            another_internal_user_id,
        }
        assert await operations.get_users_with_setting(_kind_2, value_3) == set()


class TestRemoveSettingForAllUsers:
    @pytest.mark.asyncio
    async def test(self, five_internal_user_ids: list[uuid.UUID]) -> None:
        value = uuid.uuid4().hex

        await operations.save_setting(five_internal_user_ids[0], _kind_1, value)

        await operations.save_setting(five_internal_user_ids[1], _kind_1, value)
        await operations.save_setting(five_internal_user_ids[1], _kind_2, value)

        await operations.save_setting(five_internal_user_ids[2], _kind_2, value)

        await operations.remove_setting_for_all_users(_kind_1)

        settings = await operations.load_settings_for_users(five_internal_user_ids[:3], [_kind_1, _kind_2])

        assert settings == {
            five_internal_user_ids[0]: {},
            five_internal_user_ids[1]: {_kind_2: value},
            five_internal_user_ids[2]: {_kind_2: value},
        }
