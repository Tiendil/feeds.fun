import contextlib
import datetime
import uuid
from typing import AsyncGenerator, cast

from ffun.core import logging
from ffun.feeds_collections import domain as fc_domain
from ffun.feeds_links import domain as fl_domain
from ffun.openai import client, entities, errors
from ffun.openai.keys_statuses import statuses
from ffun.resources import domain as r_domain
from ffun.resources.entities import Resource
from ffun.user_settings import domain as us_domain
from ffun.user_settings.entities import UserSettings

logger = logging.get_module_logger()


# Note: this code is not about billing, it is about protection from the overuse of keys
#       i.e. in case of a problem, we should count a key as used with a maximum used tokens


async def _api_key_is_working(api_key: str) -> bool:
    status = statuses.get(api_key)

    if status == entities.KeyStatus.works:
        return True

    if status != entities.KeyStatus.unknown:
        return False

    new_status = await client.check_api_key(api_key)

    return new_status == entities.KeyStatus.works


# TODO: add lock here to not check the same key in parallel by different processors
async def _filter_out_users_with_wrong_keys(users: dict[uuid.UUID, UserSettings]) -> dict[uuid.UUID, UserSettings]:
    from ffun.application.user_settings import UserSetting

    log = logger.bind(function="_filter_out_users_with_wrong_keys")

    log.info("start", users=list(users.keys()))

    filtered_users = {}

    for user_id, settings in users.items():
        api_key = settings.get(UserSetting.openai_api_key)

        assert api_key

        if not await _api_key_is_working(api_key):
            continue

        filtered_users[user_id] = settings

    log.info("finish", filtered_users=list(filtered_users.keys()))

    return filtered_users


def _filter_out_users_without_keys(users: dict[uuid.UUID, UserSettings]) -> dict[uuid.UUID, UserSettings]:
    from ffun.application.user_settings import UserSetting
    return {user_id: settings
            for user_id, settings in users.items()
            if settings.get(UserSetting.openai_api_key)}


_day_secods = 24 * 60 * 60


def _is_entry_new_enough(entry_age: datetime.timedelta, settings: UserSettings) -> bool:
    from ffun.application.user_settings import UserSetting

    days = settings.get(UserSetting.openai_process_entries_not_older_than)

    assert days is not None
    assert isinstance(days, int)

    return days * _day_secods >= entry_age.total_seconds()


def _filter_out_users_for_whome_entry_is_too_old(users: dict[uuid.UUID, UserSettings],
                                                 entry_age: datetime.timedelta) -> dict[uuid.UUID, UserSettings]:
    return {user_id: settings
            for user_id, settings in users.items()
            if _is_entry_new_enough(entry_age, settings)}


async def _filter_out_users_with_overused_keys(users: dict[uuid.UUID, UserSettings],
                                               reserved_tokens: int,
                                               resources: dict[uuid.UUID, Resource]) -> dict[uuid.UUID, UserSettings]:
    from ffun.application.user_settings import UserSetting

    users_with_resources = {}

    for user_id, settings in users.items():
        total = resources[user_id].total
        limit = settings.get(UserSetting.openai_max_tokens_in_month)

        assert limit is not None

        if total + reserved_tokens <= limit:
            users_with_resources[user_id] = settings
            continue

    return users_with_resources


async def _users_for_feed(feed_id: uuid.UUID) -> set[uuid.UUID]:
    from ffun.application.user_settings import UserSetting

    user_ids = await fl_domain.get_linked_users(feed_id)

    # find all users for collections
    if await fc_domain.is_feed_in_collections(feed_id):
        collections_user_ids = await us_domain.get_users_with_setting(
            UserSetting.openai_allow_use_key_for_collections, True
        )
        user_ids.extend(collections_user_ids)

    return set(user_ids)


async def _choose_user(candidates: list[uuid.UUID],
                       users: dict[uuid.UUID, UserSettings],
                       resources: dict[uuid.UUID, Resource],
                       reserved_tokens: int,
                       interval_started_at: datetime.datetime) -> uuid.UUID:
    from ffun.application.resources import Resource as AppResource
    from ffun.application.user_settings import UserSetting

    for user_id in candidates:
        settings = users[user_id]

        limit = settings.get(UserSetting.openai_max_tokens_in_month)

        assert limit is not None

        if await r_domain.try_to_reserve(
            user_id=user_id,
            kind=AppResource.openai_tokens,
            interval_started_at=interval_started_at,
            amount=reserved_tokens,
            limit=limit,
        ):
            return user_id

    raise errors.NoKeyFoundForFeed()


@contextlib.asynccontextmanager
async def _use_key(user_id: uuid.UUID,
                   api_key: str,
                   reserved_tokens: int,
                   interval_started_at: datetime.datetime) -> AsyncGenerator[entities.APIKeyUsage, None]:
    from ffun.application.resources import Resource as AppResource

    log = logger.bind(function="_use_key", user_id=user_id)

    key_usage = entities.APIKeyUsage(user_id=user_id, api_key=api_key, used_tokens=None)

    used_tokens = reserved_tokens

    try:
        log.info("provide_key")

        yield key_usage

        assert key_usage.used_tokens is not None

        used_tokens = key_usage.used_tokens

        log.info("key_used", used_tokens=used_tokens)

    finally:
        log.info(
            "convert_reserved_to_used", reserved_tokens=reserved_tokens, used_tokens=used_tokens
        )

        await r_domain.convert_reserved_to_used(
            user_id=user_id,
            kind=AppResource.openai_tokens,
            interval_started_at=interval_started_at,
            used=used_tokens,
            reserved=reserved_tokens,
        )

        log.info("resources_converted")


@contextlib.asynccontextmanager
async def api_key_for_feed_entry(  # noqa: CCR001,CFQ001
    feed_id: uuid.UUID, entry_age: datetime.timedelta, reserved_tokens: int
) -> AsyncGenerator[entities.APIKeyUsage, None]:
    # TODO: in general, openai module should not depends on application
    #       do something with that
    from ffun.application.resources import Resource as AppResource
    from ffun.application.user_settings import UserSetting

    log = logger.bind(function="api_key_for_feed_entry", feed_id=feed_id)

    log.info("start", entry_age=entry_age, reserved_tokens=reserved_tokens)

    user_ids = await _users_for_feed(feed_id)

    log.info("users_for_feed", user_ids=user_ids)

    # get api keys and limits for this users
    users = await us_domain.load_settings_for_users(
        user_ids,
        kinds=[
            UserSetting.openai_api_key,
            UserSetting.openai_max_tokens_in_month,
            UserSetting.openai_process_entries_not_older_than,
        ],
    )

    log.info("users_settings_loaded")

    users = _filter_out_users_without_keys(users)

    log.info("filtered_users_with_keys", users=list(users.keys()))

    users = _filter_out_users_for_whome_entry_is_too_old(users, entry_age)

    log.info("filtered_users_by_entry_age", users=list(users.keys()))

    users = await _filter_out_users_with_wrong_keys(users)

    log.info("filtered_users_with_working_keys", users=list(users.keys()))

    # TODO: move out this function?
    interval_started_at = r_domain.month_interval_start()

    resources = await r_domain.load_resources(
        user_ids=users.keys(), kind=AppResource.openai_tokens, interval_started_at=interval_started_at
    )

    users = await _filter_out_users_with_overused_keys(users, reserved_tokens, resources)

    log.info("filtered_users_with_enough_tokens", users=list(users.keys()))

    # sort by minimal usage
    candidate_user_ids = sorted(users.keys(), key=lambda user_id: cast(int, resources[user_id].total))

    found_user_id = await _choose_user(candidates=candidate_user_ids,
                                       users=users,
                                       resources=resources,
                                       reserved_tokens=reserved_tokens,
                                       interval_started_at=interval_started_at)

    api_key = users[found_user_id].get(UserSetting.openai_api_key)

    assert api_key is not None

    async with _use_key(user_id=found_user_id,
                        api_key=api_key,
                        reserved_tokens=reserved_tokens,
                        interval_started_at=interval_started_at) as key_usage:
        yield key_usage

    log.info("finish")
