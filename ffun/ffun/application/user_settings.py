import enum
from decimal import Decimal

from ffun.user_settings import types
from ffun.user_settings.values import Value, user_settings


class UserSetting(enum.IntEnum):
    # TODO: add gemini key
    openai_api_key = 1

    # openai_max_tokens_in_month = 2  # noqa

    # TODO: rename and update for Gemini
    hide_message_about_setting_up_key = 3

    process_entries_not_older_than = 4

    # openai_allow_use_key_for_collections = 5  # noqa

    max_tokens_cost_in_month = 6

    gemini_api_key = 7
    test_api_key = 8

    hide_message_about_adding_collections = 9
    hide_message_check_your_feed_urls = 10


_key_rules = """\
Here's how your API key will be used:

- It will only be used for your feeds.
- It will not be used for predefined collections or any other purposes.
- You can set a spending limit; we'll stop using the key if the limit is exceeded.
- If a feed has multiple subscribers with keys, we'll use the key with the lowest usage in the current month.
- API key usage statistics are available on this page.

The more users set up a key, the cheaper Feeds Fun becomes for everyone.
"""


description_openai_api_key = f"""
Feeds Fun can use OpenAI ChatGPT to determine tags for texts.

Because, for now, our service is free to use and OpenAI API costs money, \
we politely ask you to set up your own OpenAI API key.

{_key_rules}
"""

description_gemini_api_key = f"""
Feeds Fun can use Google Gemini to determine tags for texts.

Because, for now, our service is free to use and OpenAI API costs money, \
we politely ask you to set up your own OpenAI API key.

{_key_rules}
"""

description_process_entries_not_older_than = """
Some feeds keep all their news, regardless of their age. If you subscribe to such a feed, \
it may eat a lot of your API key resources.

To prevent this, we limit the age of news to be processed with your OpenAI key.

If you want to help us and tag everything, you can set this value to a big number, like 100500.
"""


description_max_tokens_cost_in_month = """
We'll stop using all your API key when the total cost of all spent tokens exceeds this value.
"""


user_settings.add(
    Value(
        key=UserSetting.openai_api_key,
        name="OpenAI API key",
        type=types.Secret(),
        default="",
        description=description_openai_api_key,
    )
)


user_settings.add(
    Value(
        key=UserSetting.gemini_api_key,
        name="Gemini API key",
        type=types.Secret(),
        default="",
        description=description_gemini_api_key,
    )
)


# TODO: hide in GUI
user_settings.add(
    Value(
        key=UserSetting.test_api_key,
        name="Test API key, YOU SHOULD NOT SEE THIS, tell to developers",
        type=types.Secret(),
        default="",
        description="",
    )
)


user_settings.add(
    Value(
        key=UserSetting.max_tokens_cost_in_month,
        name="Max spendings on API keys USD/month",
        type=types.Decimal(),
        default=Decimal("10"),
        description=description_max_tokens_cost_in_month,
    )
)


user_settings.add(
    Value(
        key=UserSetting.hide_message_about_setting_up_key,
        name="Hide message about setting up API keys",
        type=types.Boolean(),
        default=False,
        description=None,
    )
)


user_settings.add(
    Value(
        key=UserSetting.process_entries_not_older_than,
        name="Use OpenAI key only for entries not older than N days",
        type=types.Integer(),
        default=1,
        description=description_process_entries_not_older_than,
    )
)


user_settings.add(
    Value(
        key=UserSetting.hide_message_about_adding_collections,
        name="Hide message about adding feeds from collections",
        type=types.Boolean(),
        default=False,
        description=None,
    )
)


user_settings.add(
    Value(
        key=UserSetting.hide_message_check_your_feed_urls,
        name="Hide message about checking your feed URLs",
        type=types.Boolean(),
        default=False,
        description=None,
    )
)
