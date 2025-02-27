import enum
from decimal import Decimal

from ffun.user_settings import types
from ffun.user_settings.values import Value, user_settings


class UserSetting(enum.IntEnum):
    openai_api_key = 1

    # openai_max_tokens_in_month = 2  # noqa

    hide_message_about_setting_up_key = 3

    process_entries_not_older_than = 4

    # openai_allow_use_key_for_collections = 5  # noqa

    max_tokens_cost_in_month = 6

    gemini_api_key = 7
    test_api_key = 8

    hide_message_about_adding_collections = 9
    hide_message_check_your_feed_urls = 10


user_settings.add(
    Value(
        key=UserSetting.openai_api_key,
        name="OpenAI API key",
        type=types.Secret(),
        default="",
    )
)


user_settings.add(
    Value(
        key=UserSetting.gemini_api_key,
        name="Gemini API key",
        type=types.Secret(),
        default="",
    )
)


user_settings.add(
    Value(
        key=UserSetting.test_api_key,
        name="Test API key, YOU SHOULD NOT SEE THIS, tell to developers",
        type=types.Secret(),
        default="",
    )
)


user_settings.add(
    Value(
        key=UserSetting.max_tokens_cost_in_month,
        name="Max spending (USD/month)",
        type=types.Decimal(),
        default=Decimal("10"),
    )
)


user_settings.add(
    Value(
        key=UserSetting.hide_message_about_setting_up_key,
        name="Hide message about setting up API keys",
        type=types.Boolean(),
        default=False,
    )
)


user_settings.add(
    Value(
        key=UserSetting.process_entries_not_older_than,
        name="Process entries not older than N days",
        type=types.Integer(),
        default=1,
    )
)


user_settings.add(
    Value(
        key=UserSetting.hide_message_about_adding_collections,
        name="Hide message about adding feeds from collections",
        type=types.Boolean(),
        default=False,
    )
)


user_settings.add(
    Value(
        key=UserSetting.hide_message_check_your_feed_urls,
        name="Hide message about checking your feed URLs",
        type=types.Boolean(),
        default=False,
    )
)
