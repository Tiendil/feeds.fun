import contextlib
import uuid

from ffun.feeds_links import domain as fl_domain
from ffun.user_settings import domain as us_domain

from . import errors


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

    # TODO: filter our not working keys
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
