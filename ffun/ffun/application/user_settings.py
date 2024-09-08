import enum
from decimal import Decimal

from ffun.user_settings import types
from ffun.user_settings.values import Value, user_settings


class UserSetting(enum.IntEnum):
    # TODO: add gemini key
    openai_api_key = 1

    # openai_max_tokens_in_month = 2

    # TODO: rename and update for Gemini
    hide_message_about_setting_up_key = 3

    process_entries_not_older_than = 4

    max_tokens_cost_in_month = 5

    gemini_api_key = 6
    test_api_key = 7


_key_rules = """\
Here's how your key will be used:

- Your key will be used only to process your feeds. We will not use it for any other purposes.
- You can set a limit on the maximum money spent on requests to API. \
We estimate spent resources and stop using your key if they exceed the limit.
- If multiple users are subscribed to a single feed, for each news item from the \
feed, we'll use a key with less money spent in the current month.
- You can find API key usage statistics on this page.

The more users set up the key, the cheaper Feeds Fun will be for everyone.
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


description_max_tokens_cost_in_month = "TODO"


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
        name="Max spendings on API keys in month",
        type=types.Decimal(),
        default=Decimal('10'),
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
