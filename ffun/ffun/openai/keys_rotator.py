nimport contextlib
import uuid

from ffun.feeds_links import domain as fl_domain
from ffun.resources import domain as r_domain
from ffun.user_settings import domain as us_domain

from . import client, entities, errors

_keys_statuses = {}


# Note: this code is not about billing, it is about protection from the overuse of keys
#       i.e. in case of a problem, we should count a key as used with a maximum used tokens


# TODO: add logging
# TODO: add lock here to not check the same key in parallel by different processors
async def _filter_out_users_with_wrong_keys(users):
    filtered_users = {}

    for user_id, settings in users.items():
        api_key = settings.get(UserSetting.openai_api_key)

        key_status = _keys_statuses.get(api_key)

        if key_status in (Nonem, entities.KeyStatus.broken):
            key_status = await client.check_api_key(api_key)
            _keys_statuses[api_key] = key_status

        if key_status == entities.KeyStatus.broken:
            continue

        if key_status == entities.KeyStatus.works:
            filtered_users[user_id] = settings
            continue

    return filtered_users


# TODO: add logging
@contextlib.asynccontextmanager
async def api_key_for_feed_entry(feed_id: uuid.UUID, reserved_tokens: int):
    # TODO: in general, openai module should not depends on application
    #       do something with that
    from ffun.application.resources import Resource
    from ffun.application.user_settings import UserSetting

    # find all users who read feed
    user_ids = await fl_domain.get_linked_users(feed_id)

    # get api keys and limits for this users
    users = await us_domain.load_settings_for_users(user_ids,
                                                    kinds=[UserSetting.openai_api_key,
                                                           UserSetting.openai_max_tokens_in_month])

    # filter out users without api keys
    users = {user_id: settings
             for user_id, settings in users.items()
             if settings.get(UserSetting.openai_api_key)}

    # filter out users with not working keys
    users = await _filter_out_users_with_wrong_keys(users)

    # filter out users with overused keys

    interval_started_at = r_domain.month_interval_start()

    resources = await r_domain.load_resources(user_ids=users.keys(),
                                              kind=Resource.openai_tokens,
                                              interval_started_at=interval_started_at)

    users = {user_id: settings
             for user_id, settings in users.items()
             if resources[user_id].total + reserved_tokens <= settings.get(UserSetting.openai_max_tokens_in_month)}

    # sort by minimal usage
    candidate_user_ids = sorted(users.keys(),
                                key=lambda user_id: resources[user_id].total)

    found_user_id = None

    for user_id in candidate_user_ids:
        if await r_domain.try_to_reserve(user_id=user_id,
                                         kind=Resource.openai_tokens,
                                         interval_started_at=interval_started_at,
                                         reserved=reserved_tokens,
                                         limit=users[user_id].get(UserSetting.openai_max_tokens_in_month)):
            found_user_id = user_id
            break
    else:
        # TODO: test behaviour
        raise errors.NoKeyFoundForFeed()

    # TODO: what in case of errors?

    key_usage = entities.APIKeyUsage(user_id=found_user_id,
                                     api_key=users[found_user_id].get(UserSetting.openai_api_key),
                                     used=None)

    used_tokens = reserved_tokens

    try:
        yield key_usage

        used_tokens = key_usage.used

    except Exception:
        # TODO: track errors like `quota exceeded`
        pass
    finally:
        r_domain.convert_reserved_to_used(user_id=found_user_id,
                                          kind=Resource.openai_tokens,
                                          interval_started_at=interval_started_at,
                                          used=used_tokens,
                                          reserved=reserved_tokens)
