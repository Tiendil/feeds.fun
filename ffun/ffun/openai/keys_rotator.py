import contextlib
import datetime
import uuid
from typing import AsyncGenerator, cast

from ffun.core import logging
from ffun.feeds_links import domain as fl_domain
from ffun.resources import domain as r_domain
from ffun.user_settings import domain as us_domain
from ffun.user_settings.entities import UserSettings

from . import client, entities, errors


logger = logging.get_module_logger()

_keys_statuses: dict[str, entities.KeyStatus] = {}


# Note: this code is not about billing, it is about protection from the overuse of keys
#       i.e. in case of a problem, we should count a key as used with a maximum used tokens


# TODO: add lock here to not check the same key in parallel by different processors
async def _filter_out_users_with_wrong_keys(users: dict[uuid.UUID, UserSettings]) -> dict[uuid.UUID, UserSettings]:
    from ffun.application.user_settings import UserSetting

    log = logger.bind(function="_filter_out_users_with_wrong_keys")

    log.info("start", users=list(users.keys()))

    filtered_users = {}

    for user_id, settings in users.items():
        api_key = settings.get(UserSetting.openai_api_key)

        assert api_key

        key_status = _keys_statuses.get(api_key)

        log.info("openai_key_status", user_id=user_id, key_status=key_status)

        if key_status in (None, entities.KeyStatus.unknown):
            log.info("check_openai_key", user_id=user_id)
            key_status = await client.check_api_key(api_key)
            _keys_statuses[api_key] = key_status
            log.info("openai_new_key_status", user_id=user_id, key_status=key_status)

        if key_status == entities.KeyStatus.broken:
            log.info("skip_broken_openai_key", user_id=user_id)
            continue

        if key_status == entities.KeyStatus.works:
            log.info("approve_openai_key", user_id=user_id)
            filtered_users[user_id] = settings
            continue

    log.info("finish", filtered_users=list(filtered_users.keys()))

    return filtered_users


_day_secods = 24 * 60 * 60


def _is_entry_new_enough(entry_age: datetime.timedelta, settings: UserSettings) -> bool:
    from ffun.application.user_settings import UserSetting

    days = settings.get(UserSetting.openai_process_entries_not_older_than)

    assert days is not None
    assert isinstance(days, int)

    return days * _day_secods >= entry_age.total_seconds()


@contextlib.asynccontextmanager
async def api_key_for_feed_entry(
    feed_id: uuid.UUID, entry_age: datetime.timedelta, reserved_tokens: int
) -> AsyncGenerator[entities.APIKeyUsage, None]:
    # TODO: in general, openai module should not depends on application
    #       do something with that
    from ffun.application.resources import Resource
    from ffun.application.user_settings import UserSetting

    log = logger.bind(function="api_key_for_feed_entry", feed_id=feed_id)

    log.info("start", entry_age=entry_age, reserved_tokens=reserved_tokens)

    # find all users who read feed
    user_ids = await fl_domain.get_linked_users(feed_id)

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

    # filter out users without api keys
    users = {user_id: settings for user_id, settings in users.items() if settings.get(UserSetting.openai_api_key)}

    log.info("filtered_users_with_keys", users=list(users.keys()))

    # filter out users that do not want to process old entries
    users = {user_id: settings for user_id, settings in users.items() if _is_entry_new_enough(entry_age, settings)}

    log.info("filtered_users_by_entry_age", users=list(users.keys()))

    # filter out users with not working keys
    users = await _filter_out_users_with_wrong_keys(users)

    log.info("filtered_users_with_working_keys")

    # filter out users with overused keys

    interval_started_at = r_domain.month_interval_start()

    log.info("current_interval", interval_started_at=interval_started_at)

    resources = await r_domain.load_resources(
        user_ids=users.keys(), kind=Resource.openai_tokens, interval_started_at=interval_started_at
    )

    users_with_resources = {}

    for user_id, settings in users.items():
        total = resources[user_id].total
        limit = settings.get(UserSetting.openai_max_tokens_in_month)

        if total + reserved_tokens <= limit:
            users_with_resources[user_id] = settings
            log.info("user_has_resources", user_id=user_id, total=total, reserved_tokens=reserved_tokens, limit=limit)
            continue

        log.info("user_has_no_resources", user_id=user_id, total=total, reserved_tokens=reserved_tokens, limit=limit)

    # sort by minimal usage
    candidate_user_ids = sorted(users_with_resources.keys(), key=lambda user_id: cast(int, resources[user_id].total))

    found_user_id = None

    for user_id in candidate_user_ids:
        limit = settings.get(UserSetting.openai_max_tokens_in_month)

        assert limit is not None

        log.info("try_to_reserve_resources", user_id=user_id, amount=reserved_tokens, limit=limit)

        if await r_domain.try_to_reserve(
            user_id=user_id,
            kind=Resource.openai_tokens,
            interval_started_at=interval_started_at,
            amount=reserved_tokens,
            limit=limit,
        ):
            log.info("resources_reserved", user_id=user_id)
            found_user_id = user_id
            break
    else:
        log.warning("no_key_found_for_feed")
        raise errors.NoKeyFoundForFeed()

    api_key = users[found_user_id].get(UserSetting.openai_api_key)

    assert api_key is not None

    key_usage = entities.APIKeyUsage(user_id=found_user_id, api_key=api_key, used_tokens=None)

    used_tokens = reserved_tokens

    try:
        log.info("provide_key", user_id=key_usage.user_id)

        yield key_usage

        assert key_usage.used_tokens is not None

        used_tokens = key_usage.used_tokens

        log.info("key_used", user_id=key_usage.user_id, used_tokens=used_tokens)

    except Exception:
        log.info("mark_key_as_unknown_because_of_error", user_id=key_usage.user_id)
        _keys_statuses[key_usage.api_key] = entities.KeyStatus.unknown
        raise
    finally:
        log.info(
            "convert_reserved_to_used", user_id=found_user_id, reserved_tokens=reserved_tokens, used_tokens=used_tokens
        )

        await r_domain.convert_reserved_to_used(
            user_id=found_user_id,
            kind=Resource.openai_tokens,
            interval_started_at=interval_started_at,
            used=used_tokens,
            reserved=reserved_tokens,
        )

        log.info("resources_converted", user_id=found_user_id)

    log.info("finish")
