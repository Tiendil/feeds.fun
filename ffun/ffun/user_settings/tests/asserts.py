from typing import Iterable

from ffun.domain.entities import UserId
from ffun.user_settings import operations
from ffun.user_settings.entities import SettingKind


async def has_settings(user_id: UserId, values: dict[int, str]) -> None:
    expected = {SettingKind(kind): value for kind, value in values.items()}
    settings = await operations.load_settings_for_users([user_id], list(expected.keys()))
    assert settings[user_id] == expected


async def has_no_settings(user_id: UserId, kinds: Iterable[int]) -> None:
    expected_kinds = {SettingKind(kind) for kind in kinds}
    settings = await operations.load_settings_for_users([user_id], expected_kinds)
    assert expected_kinds - set(settings[user_id]) == expected_kinds
