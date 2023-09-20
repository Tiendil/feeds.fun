import uuid
from typing import Any

import pytest
import pytest_asyncio
from pytest_mock import MockerFixture

from ffun.openai.entities import KeyStatus, UserKeyInfo
from ffun.openai.keys_rotator import _get_user_key_infos
from ffun.openai.keys_statuses import statuses
from ffun.resources import domain as r_domain
from ffun.user_settings import domain as us_domain


class MockedOpenAIClient:
    def __init__(self, check_api_key: Any, request: Any) -> None:
        self.check_api_key = check_api_key
        self.request = request


async def _fake_check_api_key(api_key: str) -> KeyStatus:
    statuses.set(api_key, KeyStatus.works)
    return KeyStatus.works


# TODO: change to session scope
@pytest.fixture(autouse=True)
def mocked_openai_client(mocker: MockerFixture) -> MockedOpenAIClient:
    """Protection from calling OpenAI API during tests."""
    check_api_key = mocker.patch("ffun.openai.client.check_api_key", _fake_check_api_key)

    request = mocker.patch("ffun.openai.client.request")

    return MockedOpenAIClient(check_api_key=check_api_key, request=request)


@pytest.fixture
def openai_key() -> str:
    return uuid.uuid4().hex


@pytest_asyncio.fixture
async def five_user_key_infos(five_internal_user_ids: list[uuid.UUID]) -> list[UserKeyInfo]:
    from ffun.application.resources import Resource as AppResource
    from ffun.application.user_settings import UserSetting

    max_tokens_in_month = 1000
    used_tokens = 345

    interval_started_at = r_domain.month_interval_start()

    for user_id in five_internal_user_ids:
        await us_domain.save_setting(user_id=user_id, kind=UserSetting.openai_api_key, value=uuid.uuid4().hex)

        await us_domain.save_setting(
            user_id=user_id, kind=UserSetting.openai_max_tokens_in_month, value=max_tokens_in_month
        )

        await us_domain.save_setting(user_id=user_id, kind=UserSetting.openai_process_entries_not_older_than, value=3)

        await r_domain.try_to_reserve(
            user_id=user_id,
            kind=AppResource.openai_tokens,
            interval_started_at=interval_started_at,
            amount=used_tokens,
            limit=max_tokens_in_month,
        )

        await r_domain.convert_reserved_to_used(
            user_id=user_id,
            kind=AppResource.openai_tokens,
            interval_started_at=interval_started_at,
            used=used_tokens,
            reserved=used_tokens,
        )

    return await _get_user_key_infos(five_internal_user_ids, interval_started_at)
