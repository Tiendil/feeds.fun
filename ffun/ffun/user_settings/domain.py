from typing import Any, Iterable

from ffun.domain.entities import UserId
from ffun.user_settings import operations
from ffun.user_settings.entities import UserSettings
from ffun.user_settings.values import SettingsRegister, user_settings


async def save_setting(user_id: UserId, kind: int, value: Any, register: SettingsRegister = user_settings) -> None:
    value_to_save = register.get(kind).type.serialize(value)

    await operations.save_setting(user_id, kind, value_to_save)


def _full_settings(values: dict[int, Any], kinds: Iterable[int], register: SettingsRegister) -> UserSettings:
    result = {}

    for kind in kinds:
        if not register.has(kind):
            continue

        entity = register.get(kind)

        if kind in values:
            result[entity.key] = entity.type.deserialize(values[kind])
            continue

        result[entity.key] = entity.default

    return result  # type: ignore


async def load_settings(
    user_id: UserId, kinds: Iterable[int], register: SettingsRegister = user_settings
) -> UserSettings:
    values = await operations.load_settings_for_users([user_id], kinds)

    loaded_settings = values[user_id] if user_id in values else {}

    return _full_settings(loaded_settings, kinds, register=register)


async def load_settings_for_users(
    user_ids: Iterable[UserId], kinds: Iterable[int], register: SettingsRegister = user_settings
) -> dict[UserId, UserSettings]:
    values = await operations.load_settings_for_users(user_ids, kinds)

    return {user_id: _full_settings(user_values, kinds, register=register) for user_id, user_values in values.items()}


async def get_users_with_setting(kind: int, value: Any, register: SettingsRegister = user_settings) -> set[UserId]:
    value_to_find = register.get(kind).type.serialize(value)

    return await operations.get_users_with_setting(kind, value_to_find)


remove_setting_for_all_users = operations.remove_setting_for_all_users


async def remove_deprecated_settings(register: SettingsRegister = user_settings) -> None:
    all_kinds = await operations.find_all_kinds()

    for kind in all_kinds:
        if register.has(kind):
            continue

        await remove_setting_for_all_users(kind)
