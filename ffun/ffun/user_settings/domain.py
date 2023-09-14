import uuid
from typing import Any, Iterable

from ffun.user_settings import operations
from ffun.user_settings.entities import UserSettings
from ffun.user_settings.values import SettingsRegister, user_settings


async def save_setting(user_id: uuid.UUID, kind: int, value: Any, register: SettingsRegister = user_settings) -> None:
    value_to_save = register.get(kind).type.serialize(value)

    await operations.save_setting(user_id, kind, value_to_save)


def _full_settings(values: dict[int, Any], kinds: Iterable[int], register: SettingsRegister) -> UserSettings:
    result = {}

    for kind in kinds:
        if kind in values:
            result[kind] = register.get(kind).type.deserialize(values[kind])
            continue

        result[kind] = register.get(kind).default

    return result


async def load_settings(
    user_id: uuid.UUID, kinds: Iterable[int], register: SettingsRegister = user_settings
) -> UserSettings:
    values = await operations.load_settings_for_users([user_id], kinds)

    loaded_settings = values[user_id] if user_id in values else {}

    return _full_settings(loaded_settings, kinds, register=register)


async def load_settings_for_users(
    user_ids: Iterable[uuid.UUID], kinds: Iterable[int], register: SettingsRegister = user_settings
) -> dict[uuid.UUID, UserSettings]:
    values = await operations.load_settings_for_users(user_ids, kinds)

    return {user_id: _full_settings(user_values, kinds, register=register) for user_id, user_values in values.items()}


async def get_users_with_setting(kind: int, value: Any, register: SettingsRegister = user_settings) -> set[uuid.UUID]:
    value_to_find = register.get(kind).type.serialize(value)

    return await operations.get_users_with_setting(kind, value_to_find)


remove_setting_for_all_users = operations.remove_setting_for_all_users
