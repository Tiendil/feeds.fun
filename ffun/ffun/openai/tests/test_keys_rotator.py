import datetime
from typing import Any, Type

import openai
import pytest
from pytest_mock import MockerFixture

from ffun.openai.entities import KeyStatus
from ffun.openai.keys_rotator import _api_key_is_working
from ffun.openai.keys_statuses import Statuses, StatusInfo, track_key_status


class TestAPIKeyIsWorking:

    @pytest.mark.asyncio
    async def test_is_working(self, statuses: Statuses) -> None:
        statuses.set('key_1', KeyStatus.works)
        assert await _api_key_is_working('key_1', statuses=statuses)

    @pytest.mark.parametrize('status', [status
                                        for status in KeyStatus
                                        if status not in [KeyStatus.works, KeyStatus.unknown]])
    @pytest.mark.asyncio
    async def test_guaranted_broken(self, status: KeyStatus, statuses: Statuses) -> None:
        statuses.set('key_1', status)
        assert not await _api_key_is_working('key_1', statuses=statuses)

    @pytest.mark.parametrize('status, expected_result', [(KeyStatus.works, True),
                                                         (KeyStatus.broken, False)])
    @pytest.mark.asyncio
    async def test_unknown(self,
                           status: KeyStatus,
                           expected_result: bool,
                           statuses: Statuses,
                           mocker: MockerFixture) -> None:
        assert statuses.get('key_1') == KeyStatus.unknown

        mocker.patch("ffun.openai.client.check_api_key", return_value=status)

        assert await _api_key_is_working('key_1',
                                         statuses=statuses) == expected_result


class TestFilterOutUsersWithWrongKeys:
    pass
