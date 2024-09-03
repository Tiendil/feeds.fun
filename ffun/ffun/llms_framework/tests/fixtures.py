import uuid
from typing import Any

import pytest
import pytest_asyncio
from pytest_mock import MockerFixture

from ffun.domain.datetime_intervals import month_interval_start
from ffun.llms_framework.entities import KeyStatus, UserKeyInfo
from ffun.llms_framework.keys_rotator import _get_user_key_infos
from ffun.resources import domain as r_domain
from ffun.user_settings import domain as us_domain


@pytest_asyncio.fixture
async def five_user_key_infos(five_internal_user_ids: list[uuid.UUID]) -> list[UserKeyInfo]:
    from ffun.application.resources import Resource as AppResource
    from ffun.application.user_settings import UserSetting

    max_tokens_in_month = 1000
    used_tokens = 345

    interval_started_at = month_interval_start()

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


@pytest.fixture
def fake_api_key() -> str:
    return uuid.uuid4().hex
