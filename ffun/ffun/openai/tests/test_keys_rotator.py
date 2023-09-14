import datetime
import uuid
from typing import Any, Type

import openai
import pytest
from pytest_mock import MockerFixture

from ffun.openai.entities import KeyStatus, UserKeyInfo
from ffun.openai.keys_rotator import (
    _api_key_is_working,
    _filter_out_users_for_whome_entry_is_too_old,
    _filter_out_users_with_overused_keys,
    _filter_out_users_with_wrong_keys,
    _filter_out_users_without_keys,
)
from ffun.openai.keys_statuses import Statuses, StatusInfo, statuses, track_key_status


class TestAPIKeyIsWorking:

    @pytest.mark.asyncio
    async def test_is_working(self, openai_key: str) -> None:
        statuses.set(openai_key, KeyStatus.works)
        assert await _api_key_is_working(openai_key)

    @pytest.mark.parametrize('status', [status
                                        for status in KeyStatus
                                        if status not in [KeyStatus.works, KeyStatus.unknown]])
    @pytest.mark.asyncio
    async def test_guaranted_broken(self, status: KeyStatus, openai_key: str) -> None:
        statuses.set(openai_key, status)
        assert not await _api_key_is_working(openai_key)

    @pytest.mark.parametrize('status, expected_result', [(KeyStatus.works, True),
                                                         (KeyStatus.broken, False)])
    @pytest.mark.asyncio
    async def test_unknown(self,
                           status: KeyStatus,
                           expected_result: bool,
                           statuses: Statuses,
                           mocker: MockerFixture,
                           openai_key: str) -> None:
        assert statuses.get(openai_key) == KeyStatus.unknown

        mocker.patch("ffun.openai.client.check_api_key", return_value=status)

        assert await _api_key_is_working(openai_key) == expected_result


class TestFilterOutUsersWithWrongKeys:

    @pytest.mark.asyncio
    async def test_empty_list(self) -> None:
        assert await _filter_out_users_with_wrong_keys([]) == []

    @pytest.mark.asyncio
    async def test_all_working(self, five_user_key_infos: list[UserKeyInfo]) -> None:
        assert five_user_key_infos[1].api_key
        assert five_user_key_infos[3].api_key

        statuses.set(five_user_key_infos[1].api_key, KeyStatus.broken)
        statuses.set(five_user_key_infos[3].api_key, KeyStatus.quota)

        infos = await _filter_out_users_with_wrong_keys(five_user_key_infos)

        assert infos == [five_user_key_infos[i] for i in [0, 2, 4]]


class TestFilterOutUsersWithoutKeys:

    def test_empty_list(self) -> None:
        assert _filter_out_users_without_keys([]) == []

    def test_all_working(self, five_user_key_infos: list[UserKeyInfo]) -> None:
        five_user_key_infos[1].api_key = None
        five_user_key_infos[3].api_key = None

        infos = _filter_out_users_without_keys(five_user_key_infos)

        assert infos == [five_user_key_infos[i] for i in [0, 2, 4]]


class TestFilterOutUsersForWhomeEntryIsTooOld:

    def test_empty_list(self) -> None:
        assert _filter_out_users_for_whome_entry_is_too_old([], datetime.timedelta(days=1)) == []

    def test_all_working(self, five_user_key_infos: list[UserKeyInfo]) -> None:
        for info, days in zip(five_user_key_infos, [5, 2, 3, 1, 4]):
            info.process_entries_not_older_than = datetime.timedelta(days=days)

        infos = _filter_out_users_for_whome_entry_is_too_old(five_user_key_infos,
                                                             datetime.timedelta(days=3))

        assert infos == [five_user_key_infos[i] for i in [0, 2, 4]]


class TestFilterOutUsersWithOverusedKeys:

    def test_empty_list(self) -> None:
        assert _filter_out_users_with_overused_keys([], 100) == []

    def test_all_working(self, five_user_key_infos: list[UserKeyInfo]) -> None:
        for info, max_tokens_in_month in zip(five_user_key_infos, [201, 100, 300, 200, 500]):
            info.tokens_used = 50
            info.max_tokens_in_month = max_tokens_in_month

        infos = _filter_out_users_with_overused_keys(five_user_key_infos, 150)

        assert infos == [five_user_key_infos[i] for i in [0, 2, 4]]
