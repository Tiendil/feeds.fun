import contextlib
import datetime
import uuid
from typing import Any, AsyncGenerator, Collection, Iterable, Protocol

from ffun.core import logging
from ffun.feeds.entities import FeedId
from ffun.feeds_collections import domain as fc_domain
from ffun.feeds_links import domain as fl_domain
from ffun.llms_framework import errors
from ffun.llms_framework.entities import APIKeyUsage, KeyStatus, LLMConfiguration, SelectKeyContext, UserKeyInfo
from ffun.llms_framework.provider_interface import ProviderInterface
from ffun.resources import domain as r_domain
from ffun.user_settings import domain as us_domain

logger = logging.get_module_logger()


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
    infos: list[UserKeyInfo], reserved_tokens: int, **kwargs: Any
) -> list[UserKeyInfo]:
    return [info for info in infos if info.tokens_used + reserved_tokens < info.max_tokens_in_month]


async def _choose_user(
    infos: list[UserKeyInfo], reserved_tokens: int, interval_started_at: datetime.datetime
) -> UserKeyInfo | None:
    from ffun.application.resources import Resource as AppResource

    for info in infos:
        if await r_domain.try_to_reserve(
            user_id=info.user_id,
            kind=AppResource.openai_tokens,
            interval_started_at=interval_started_at,
            amount=reserved_tokens,
            limit=info.max_tokens_in_month,
        ):
            return info

    return None


async def _get_user_key_infos(
    user_ids: Iterable[uuid.UUID], interval_started_at: datetime.datetime
) -> list[UserKeyInfo]:
    from ffun.application.resources import Resource as AppResource
    from ffun.application.user_settings import UserSetting

    users_settings = await us_domain.load_settings_for_users(
        user_ids,
        kinds=[
            UserSetting.openai_api_key,
            UserSetting.openai_max_tokens_in_month,
            UserSetting.openai_process_entries_not_older_than,
        ],
    )

    resources = await r_domain.load_resources(
        user_ids=user_ids, kind=AppResource.openai_tokens, interval_started_at=interval_started_at
    )

    infos = []

    for user_id in user_ids:
        settings = users_settings[user_id]

        days = settings.get(UserSetting.openai_process_entries_not_older_than)

        assert days is not None
        assert isinstance(days, int)

        max_tokens_in_month = settings.get(UserSetting.openai_max_tokens_in_month)

        assert max_tokens_in_month is not None
        assert isinstance(max_tokens_in_month, int)

        infos.append(
            UserKeyInfo(
                user_id=user_id,
                api_key=settings.get(UserSetting.openai_api_key),
                max_tokens_in_month=max_tokens_in_month,
                process_entries_not_older_than=datetime.timedelta(days=days),
                tokens_used=resources[user_id].total,
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
    feed_id: FeedId,
    interval_started_at: datetime.datetime,
    entry_age: datetime.timedelta,
    reserved_tokens: int,
    filters: tuple[Any, ...] = _filters,
) -> list[UserKeyInfo]:
    user_ids = await fl_domain.get_linked_users(feed_id)

    infos = await _get_user_key_infos(user_ids, interval_started_at)

    for _filter in filters:
        if not infos:
            return []

        infos = await _filter(
            llm=llm, llm_config=llm_config, infos=infos, entry_age=entry_age, reserved_tokens=reserved_tokens
        )

    return infos


async def _find_best_user_with_key(
    llm: ProviderInterface,
    llm_config: LLMConfiguration,
    feed_id: FeedId,
    entry_age: datetime.timedelta,
    interval_started_at: datetime.datetime,
    reserved_tokens: int,
) -> UserKeyInfo | None:
    infos = await _get_candidates(
        llm=llm,
        llm_config=llm_config,
        feed_id=feed_id,
        interval_started_at=interval_started_at,
        entry_age=entry_age,
        reserved_tokens=reserved_tokens,
    )

    infos.sort(key=lambda info: info.tokens_used)

    return await _choose_user(infos=infos, reserved_tokens=reserved_tokens, interval_started_at=interval_started_at)


####################
# choosing key logic
####################


async def _choose_general_key(llm: ProviderInterface, context: SelectKeyContext) -> APIKeyUsage | None:

    key = context.general_api_key

    if key is None:
        return None

    return APIKeyUsage(
        user_id=None,
        api_key=key,
        reserved_tokens=context.reserved_tokens,
        used_tokens=None,
        interval_started_at=context.interval_started_at,
    )


async def _choose_collections_key(llm: ProviderInterface, context: SelectKeyContext) -> APIKeyUsage | None:

    key = context.collections_api_key

    if key is None:
        return None

    if not await fc_domain.is_feed_in_collections(context.feed_id):
        return None

    return APIKeyUsage(
        user_id=None,
        api_key=key,
        reserved_tokens=context.reserved_tokens,
        used_tokens=None,
        interval_started_at=context.interval_started_at,
    )


async def _choose_user_key(llm: ProviderInterface, context: SelectKeyContext) -> APIKeyUsage | None:

    if await fc_domain.is_feed_in_collections(context.feed_id):
        raise errors.FeedsFromCollectionsMustNotBeProcessedWithUserAPIKeys(feed_id=context.feed_id)

    info = await _find_best_user_with_key(
        llm=llm,
        llm_config=context.llm_config,
        feed_id=context.feed_id,
        entry_age=context.entry_age,
        interval_started_at=context.interval_started_at,
        reserved_tokens=context.reserved_tokens,
    )

    if info is None:
        return None

    if info.api_key is None:
        raise NotImplementedError("imporssible keys")

    return APIKeyUsage(
        user_id=info.user_id,
        api_key=info.api_key,
        reserved_tokens=context.reserved_tokens,
        used_tokens=None,
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

    log = logger.bind(function="_use_key", user_id=key_usage.user_id)

    try:
        yield

        if key_usage.used_tokens is None:
            raise errors.UsedTokensHasNotSpecified()

        log.info("key_used", used_tokens=key_usage.used_tokens)

    finally:
        log.info(
            "convert_reserved_to_used", reserved_tokens=key_usage.reserved_tokens, used_tokens=key_usage.used_tokens
        )

        if key_usage.user_id is not None:
            await r_domain.convert_reserved_to_used(
                user_id=key_usage.user_id,
                kind=AppResource.openai_tokens,
                interval_started_at=key_usage.interval_started_at,
                used=key_usage.spent_tokens(),
                reserved=key_usage.reserved_tokens,
            )

        log.info("resources_converted")
