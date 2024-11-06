import contextlib
import datetime
from decimal import Decimal
from typing import Any, AsyncGenerator, Collection, Iterable, Protocol

from ffun.core import logging
from ffun.domain.entities import UserId
from ffun.feeds.entities import FeedId
from ffun.feeds_collections.collections import collections
from ffun.feeds_links import domain as fl_domain
from ffun.llms_framework import errors
from ffun.llms_framework.entities import (
    APIKeyUsage,
    KeyStatus,
    LLMApiKey,
    LLMConfiguration,
    LLMProvider,
    SelectKeyContext,
    USDCost,
    UserKeyInfo,
)
from ffun.llms_framework.provider_interface import ProviderInterface
from ffun.resources import domain as r_domain
from ffun.user_settings import domain as us_domain

logger = logging.get_module_logger()


# TODO: cost
class CostPoints:
    __slots__ = ("_k",)

    def __init__(self, k: int) -> None:
        self._k = k

    def to_cost(self, points: int) -> USDCost:
        return USDCost(Decimal(points) / self._k)

    def to_points(self, cost: USDCost) -> int:
        return int(cost * self._k)


_cost_points = CostPoints(k=1_000_000_000)


# Note: this code is not about billing, it is about protection from the overuse of keys
#       i.e. in case of a problem, we should count a key as used with a maximum used tokens


class KeySelector(Protocol):
    async def __call__(self, llm: ProviderInterface, context: SelectKeyContext) -> APIKeyUsage | None:
        """Selector function"""


#######################
# filtering users logic
#######################


# TODO: add lock here to not check the same key in parallel by different processors
async def _api_key_is_working(llm: ProviderInterface, llm_config: LLMConfiguration, api_key: str) -> bool:
    status = llm.api_keys_statuses.get(api_key)

    if status == KeyStatus.works:
        return True

    if status != KeyStatus.unknown:
        return False

    new_status = await llm.check_api_key(llm_config, api_key)

    return new_status == KeyStatus.works


async def _filter_out_users_with_wrong_keys(
    llm: ProviderInterface, llm_config: LLMConfiguration, infos: list[UserKeyInfo], **kwargs: Any
) -> list[UserKeyInfo]:
    return [info for info in infos if info.api_key and await _api_key_is_working(llm, llm_config, info.api_key)]


async def _filter_out_users_without_keys(infos: list[UserKeyInfo], **kwargs: Any) -> list[UserKeyInfo]:
    return [info for info in infos if info.api_key]


async def _filter_out_users_for_whome_entry_is_too_old(
    infos: list[UserKeyInfo], entry_age: datetime.timedelta, **kwargs: Any
) -> list[UserKeyInfo]:
    return [info for info in infos if info.process_entries_not_older_than >= entry_age]


async def _filter_out_users_with_overused_keys(
    infos: list[UserKeyInfo], reserved_cost: USDCost, **kwargs: Any
) -> list[UserKeyInfo]:
    return [info for info in infos if info.cost_used + reserved_cost < info.max_tokens_cost_in_month]


async def _choose_user(
    infos: list[UserKeyInfo], reserved_cost: USDCost, interval_started_at: datetime.datetime
) -> UserKeyInfo | None:
    from ffun.application.resources import Resource as AppResource

    for info in infos:

        if await r_domain.try_to_reserve(
            user_id=info.user_id,
            kind=AppResource.tokens_cost,
            interval_started_at=interval_started_at,
            amount=_cost_points.to_points(reserved_cost),
            limit=_cost_points.to_points(info.max_tokens_cost_in_month),
        ):
            return info

    return None


# TODO: test that works for openai and gemini
async def _get_user_key_infos(  # pylint: disable=R0914
    provider: LLMProvider, user_ids: Iterable[UserId], interval_started_at: datetime.datetime
) -> list[UserKeyInfo]:
    from ffun.application.resources import Resource as AppResource
    from ffun.application.user_settings import UserSetting

    # TODO: move somewhere in configs
    provider_to_settings = {
        LLMProvider.openai: UserSetting.openai_api_key,
        LLMProvider.google: UserSetting.gemini_api_key,
        LLMProvider.test: UserSetting.test_api_key,
    }

    key_setting = provider_to_settings[provider]

    kinds = [UserSetting.max_tokens_cost_in_month, UserSetting.process_entries_not_older_than, key_setting]

    users_settings = await us_domain.load_settings_for_users(
        user_ids,
        kinds=kinds,
    )

    resources = await r_domain.load_resources(
        user_ids=user_ids, kind=AppResource.tokens_cost, interval_started_at=interval_started_at
    )

    infos = []

    for user_id in user_ids:
        settings = users_settings[user_id]

        days = settings.get(UserSetting.process_entries_not_older_than)
        assert days is not None
        assert isinstance(days, int)

        max_tokens_cost_in_month_raw = settings.get(UserSetting.max_tokens_cost_in_month)
        assert isinstance(max_tokens_cost_in_month_raw, Decimal)
        max_tokens_cost_in_month = USDCost(max_tokens_cost_in_month_raw)

        api_key_raw = settings.get(key_setting)
        assert isinstance(api_key_raw, str)
        api_key = LLMApiKey(api_key_raw)

        infos.append(
            UserKeyInfo(
                user_id=user_id,
                api_key=api_key,
                max_tokens_cost_in_month=max_tokens_cost_in_month,
                process_entries_not_older_than=datetime.timedelta(days=days),
                cost_used=_cost_points.to_cost(resources[user_id].total),
            )
        )

    return infos


_filters = (
    _filter_out_users_without_keys,
    _filter_out_users_for_whome_entry_is_too_old,
    _filter_out_users_with_wrong_keys,
    _filter_out_users_with_overused_keys,
)


async def _get_candidates(  # noqa
    llm: ProviderInterface,
    llm_config: LLMConfiguration,
    feed_ids: set[FeedId],
    interval_started_at: datetime.datetime,
    entry_age: datetime.timedelta,
    reserved_cost: USDCost,
    filters: tuple[Any, ...] = _filters,
) -> list[UserKeyInfo]:
    user_ids = await fl_domain.get_linked_users_flat(feed_ids)

    infos = await _get_user_key_infos(llm.provider, user_ids, interval_started_at)

    for _filter in filters:

        if not infos:
            return []

        infos = await _filter(
            llm=llm, llm_config=llm_config, infos=infos, entry_age=entry_age, reserved_cost=reserved_cost
        )

    return infos


async def _find_best_user_with_key(
    llm: ProviderInterface,
    llm_config: LLMConfiguration,
    feed_ids: set[FeedId],
    entry_age: datetime.timedelta,
    interval_started_at: datetime.datetime,
    reserved_cost: USDCost,
) -> UserKeyInfo | None:
    infos = await _get_candidates(
        llm=llm,
        llm_config=llm_config,
        feed_ids=feed_ids,
        interval_started_at=interval_started_at,
        entry_age=entry_age,
        reserved_cost=reserved_cost,
    )

    infos.sort(key=lambda info: info.cost_used)

    return await _choose_user(infos=infos, reserved_cost=reserved_cost, interval_started_at=interval_started_at)


####################
# choosing key logic
####################


async def _choose_general_key(llm: ProviderInterface, context: SelectKeyContext) -> APIKeyUsage | None:

    key = context.general_api_key

    if key is None:
        return None

    return APIKeyUsage(
        provider=llm.provider,
        user_id=None,
        api_key=key,
        reserved_cost=context.reserved_cost,
        input_tokens=None,
        output_tokens=None,
        used_cost=None,
        interval_started_at=context.interval_started_at,
    )


async def _choose_collections_key(llm: ProviderInterface, context: SelectKeyContext) -> APIKeyUsage | None:

    key = context.collections_api_key

    if key is None:
        return None

    if all(not collections.has_feed(feed_id) for feed_id in context.feed_ids):
        return None

    return APIKeyUsage(
        provider=llm.provider,
        user_id=None,
        api_key=key,
        reserved_cost=context.reserved_cost,
        input_tokens=None,
        output_tokens=None,
        used_cost=None,
        interval_started_at=context.interval_started_at,
    )


async def _choose_user_key(llm: ProviderInterface, context: SelectKeyContext) -> APIKeyUsage | None:

    if any(collections.has_feed(feed_id) for feed_id in context.feed_ids):
        raise errors.FeedsFromCollectionsMustNotBeProcessedWithUserAPIKeys(feed_ids=context.feed_ids)

    info = await _find_best_user_with_key(
        llm=llm,
        llm_config=context.llm_config,
        feed_ids=context.feed_ids,
        entry_age=context.entry_age,
        interval_started_at=context.interval_started_at,
        reserved_cost=context.reserved_cost,
    )

    if info is None:
        return None

    if info.api_key is None:
        raise NotImplementedError("imporssible keys")

    return APIKeyUsage(
        provider=llm.provider,
        user_id=info.user_id,
        api_key=info.api_key,
        reserved_cost=context.reserved_cost,
        input_tokens=None,
        output_tokens=None,
        used_cost=None,
        interval_started_at=context.interval_started_at,
    )


# Collections key has priority over general key
# Because otherwise there will be not possible to use general key only for users
_key_selectors: Collection[KeySelector] = (_choose_collections_key, _choose_general_key, _choose_user_key)


async def choose_api_key(
    llm: ProviderInterface, context: SelectKeyContext, selectors: Iterable[KeySelector] = _key_selectors
) -> APIKeyUsage | None:
    for key_selector in selectors:
        key_usage = await key_selector(llm, context)

        if key_usage is not None:
            return key_usage

    return None


#################
# key usage logic
#################


@contextlib.asynccontextmanager
async def use_api_key(key_usage: APIKeyUsage) -> AsyncGenerator[None, None]:
    from ffun.application.resources import Resource as AppResource
    from ffun.llms_framework.providers import llm_providers

    log = logger.bind(function="_use_key", user_id=key_usage.user_id)

    try:
        yield

        if key_usage.used_cost is None:
            raise errors.UsedTokensHasNotSpecified()

        log.info("used_cost", used_cost=key_usage.used_cost)

    finally:
        log.info("convert_reserved_to_used", reserved_cost=key_usage.reserved_cost, used_cost=key_usage.used_cost)

        new_key_status = llm_providers.get(key_usage.provider).provider.api_keys_statuses.get(key_usage.api_key)

        log.business_event(  # type: ignore
            "llm_api_key_used",
            user_id=key_usage.user_id,
            llm_provider=key_usage.provider,
            new_key_status=new_key_status,
        )

        if key_usage.user_id is not None:
            await r_domain.convert_reserved_to_used(
                user_id=key_usage.user_id,
                kind=AppResource.tokens_cost,
                interval_started_at=key_usage.interval_started_at,
                used=_cost_points.to_points(key_usage.cost_to_register()),
                reserved=_cost_points.to_points(key_usage.reserved_cost),
            )

        log.info("resources_converted")
