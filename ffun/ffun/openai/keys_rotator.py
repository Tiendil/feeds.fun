import contextlib
import uuid

from ffun.feeds_links import domain as fl_domain
from ffun.user_settings import domain as us_domain

from . import client, entities, errors

_keys_statuses = {}


# Note: this code is not about billing, it is about protection from the overuse of keys
#       i.e. in case of a problem, we should count a key as used with a maximum used tokens


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


@contextlib.asynccontextmanager
async def api_key_for_feed_entry(feed_id: uuid.UUID, reserved_tokens: int):
    # TODO: in general, openai module should not depends on application
    #       do something with that
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

    # filter out not working keys
    users = await _filter_out_users_with_wrong_keys(users)

    # TODO: filter out overused keys
    # TODO: sort by minimal usage

    keys = [settings[UserSetting.openai_api_key]
            for settings in users.values()]

    # raise if no api keys found
    if not keys:
        # TODO: test behaviour
        raise errors.NoKeyFoundForFeed()

    # choose first

    api_key = keys[0]

    # TODO: reserve usage

    try:
        yield api_key
    finally:
        # TODO: fix usage
        pass
