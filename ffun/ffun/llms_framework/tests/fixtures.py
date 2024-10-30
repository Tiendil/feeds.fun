import uuid
from decimal import Decimal

import pytest
import pytest_asyncio

from ffun.domain.datetime_intervals import month_interval_start
from ffun.domain.entities import UserId
from ffun.llms_framework.entities import LLMApiKey, LLMProvider, USDCost, UserKeyInfo
from ffun.llms_framework.keys_rotator import _cost_points, _get_user_key_infos
from ffun.llms_framework.keys_statuses import Statuses
from ffun.llms_framework.provider_interface import ProviderTest
from ffun.resources import domain as r_domain
from ffun.user_settings import domain as us_domain


# TODO: replace LLMProvider.openai with LLMProvider.test
@pytest_asyncio.fixture
async def five_user_key_infos(
    fake_llm_provider: ProviderTest, five_internal_user_ids: list[UserId]
) -> list[UserKeyInfo]:
    from ffun.application.resources import Resource as AppResource
    from ffun.application.user_settings import UserSetting

    max_tokens_cost_in_month = USDCost(Decimal(1000))
    used_cost = USDCost(Decimal(345))

    interval_started_at = month_interval_start()

    for user_id in five_internal_user_ids:
        await us_domain.save_setting(user_id=user_id, kind=UserSetting.test_api_key, value=uuid.uuid4().hex)

        await us_domain.save_setting(
            user_id=user_id, kind=UserSetting.max_tokens_cost_in_month, value=max_tokens_cost_in_month
        )

        await us_domain.save_setting(user_id=user_id, kind=UserSetting.process_entries_not_older_than, value=3)

        await r_domain.try_to_reserve(
            user_id=user_id,
            kind=AppResource.tokens_cost,
            interval_started_at=interval_started_at,
            amount=_cost_points.to_points(used_cost),
            limit=_cost_points.to_points(max_tokens_cost_in_month),
        )

        await r_domain.convert_reserved_to_used(
            user_id=user_id,
            kind=AppResource.tokens_cost,
            interval_started_at=interval_started_at,
            used=_cost_points.to_points(used_cost),
            reserved=_cost_points.to_points(used_cost),
        )

    return await _get_user_key_infos(LLMProvider.test, five_internal_user_ids, interval_started_at)


@pytest.fixture
def fake_llm_api_key() -> LLMApiKey:
    return LLMApiKey(uuid.uuid4().hex)


@pytest.fixture
def api_key_statuses() -> Statuses:
    return Statuses()


@pytest.fixture
def fake_llm_provider() -> ProviderTest:
    return ProviderTest()
