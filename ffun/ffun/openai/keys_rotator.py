import contextlib
import datetime
import uuid
from typing import Any, AsyncGenerator, Iterable

from ffun.core import logging
from ffun.feeds.entities import FeedId
from ffun.feeds_collections import domain as fc_domain
from ffun.feeds_links import domain as fl_domain
from ffun.openai import client, entities, errors
from ffun.openai.keys_statuses import statuses
from ffun.openai.settings import settings
from ffun.resources import domain as r_domain
from ffun.user_settings import domain as us_domain

logger = logging.get_module_logger()


# Note: this code is not about billing, it is about protection from the overuse of keys
#       i.e. in case of a problem, we should count a key as used with a maximum used tokens


# TODO: add lock here to not check the same key in parallel by different processors
async def _api_key_is_working(api_key: str) -> bool:
    status = statuses.get(api_key)

    if status == entities.KeyStatus.works:
        return True

    if status != entities.KeyStatus.unknown:
        return False

    new_status = await client.check_api_key(api_key)

    return new_status == entities.KeyStatus.works


async def _filter_out_users_with_wrong_keys(
    infos: list[entities.UserKeyInfo], **kwargs: Any
) -> list[entities.UserKeyInfo]:
    return [info for info in infos if info.api_key and await _api_key_is_working(info.api_key)]


async def _filter_out_users_without_keys(
    infos: list[entities.UserKeyInfo], **kwargs: Any
) -> list[entities.UserKeyInfo]:
    return [info for info in infos if info.api_key]


async def _filter_out_users_for_whome_entry_is_too_old(
    infos: list[entities.UserKeyInfo], entry_age: datetime.timedelta, **kwargs: Any
) -> list[entities.UserKeyInfo]:
    return [info for info in infos if info.process_entries_not_older_than >= entry_age]


async def _filter_out_users_with_overused_keys(
    infos: list[entities.UserKeyInfo], reserved_tokens: int, **kwargs: Any
) -> list[entities.UserKeyInfo]:
    return [info for info in infos if info.tokens_used + reserved_tokens < info.max_tokens_in_month]


async def _choose_user(
    infos: list[entities.UserKeyInfo], reserved_tokens: int, interval_started_at: datetime.datetime
) -> entities.UserKeyInfo | None:
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


# TODO: tests
@contextlib.asynccontextmanager
async def use_api_key(key_usage: entities.APIKeyUsage) -> AsyncGenerator[None, None]:
    from ffun.application.resources import Resource as AppResource

    log = logger.bind(function="_use_key", user_id=key_usage.user_id)

    try:
        yield

        if key_usage.used_tokens is None:
            raise NotImplementedError()

        log.info("key_used", used_tokens=key_usage.used_tokens)

    finally:
        log.info("convert_reserved_to_used", reserved_tokens=reserved_tokens, used_tokens=used_tokens)

        await r_domain.convert_reserved_to_used(
            user_id=key_usage.user_id,
            kind=AppResource.openai_tokens,
            interval_started_at=key_usage.interval_started_at,
            used=key_usage.spent_tokens(),
            reserved=key_usage.reserved_tokens,
        )

        log.info("resources_converted")


async def _get_user_key_infos(
    user_ids: Iterable[uuid.UUID], interval_started_at: datetime.datetime
) -> list[entities.UserKeyInfo]:
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
            entities.UserKeyInfo(
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


async def _get_candidates(
    feed_id: FeedId,
    interval_started_at: datetime.datetime,
    entry_age: datetime.timedelta,
    reserved_tokens: int,
    filters: tuple[Any, ...] = _filters,
) -> list[entities.UserKeyInfo]:
    user_ids = await fl_domain.get_linked_users(feed_id)

    infos = await _get_user_key_infos(user_ids, interval_started_at)

    for _filter in filters:
        if not infos:
            return []

        infos = await _filter(infos=infos, entry_age=entry_age, reserved_tokens=reserved_tokens)

    return infos


async def _find_best_user_with_key(
    feed_id: FeedId, entry_age: datetime.timedelta, interval_started_at: datetime.datetime, reserved_tokens: int
) -> entities.UserKeyInfo | None:
    infos = await _get_candidates(
        feed_id=feed_id, interval_started_at=interval_started_at, entry_age=entry_age, reserved_tokens=reserved_tokens
    )

    infos.sort(key=lambda info: info.tokens_used)

    return await _choose_user(infos=infos, reserved_tokens=reserved_tokens, interval_started_at=interval_started_at)


####################
# choosing key logic
####################

async def _choose_general_key(context: entities.SelectKeyContext) -> entities.APIKeyUsage | None:
    if settings.general_api_key is None:
        return None

    return entities.APIKeyUsage(user_id=uuid.UUID(int=0),
                                api_key=settings.general_api_key,
                                reserved_tokens=context.reserved_tokens,
                                used_tokens=None,
                                interval_started_at=context.interval_started_at)


async def _choose_collections_key(context: entities.SelectKeyContext) -> entities.APIKeyUsage | None:
    if settings.collections_api_key is None:
        return None

    if not await fc_domain.is_feed_in_collections(context.feed_id):
        return None

    return entities.APIKeyUsage(user_id=uuid.UUID(int=0),
                                api_key=settings.collections_api_key,
                                reserved_tokens=context.reserved_tokens,
                                used_tokens=None,
                                interval_started_at=context.interval_started_at)


# TODO: test
async def _choose_user_key(context: entities.SelectKeyContext) -> entities.APIKeyUsage | None:
    info = await _find_best_user_with_key(
        feed_id=context.feed_id,
        entry_age=context.entry_age,
        interval_started_at=context.interval_started_at,
        reserved_tokens=context.reserved_tokens
    )

    if info is None:
        return None

    return entities.APIKeyUsage(user_id=info.user_id,
                                api_key=info.api_key,
                                reserved_tokens=context.reserved_tokens,
                                used_tokens=None,
                                interval_started_at=context.interval_started_at)


_key_selectors = (_choose_general_key, _choose_collections_key, _choose_user_key)


# TODO: tests
async def choose_api_key(context: entities.SelectKeyContext,
                         selectors: Iterable[entities.KeySelector] = _key_selectors) -> entities.APIKeyUsage:
    for key_selector in selectors:
        key_usage = await key_selector(context)

        if key_usage is not None:
            return key_usage

    raise errors.NoKeyFoundForFeed()
