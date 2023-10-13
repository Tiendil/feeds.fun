import decimal
import enum

from ffun.user_settings import types
from ffun.user_settings.values import Value, user_settings


class UserSetting(enum.IntEnum):
    openai_api_key = 1
    openai_max_tokens_in_month = 2
    openai_hide_message_about_setting_up_key = 3
    openai_process_entries_not_older_than = 4
    openai_allow_use_key_for_collections = 5


description_openai_api_key = """
Feeds Fun uses OpenAI ChatGPT to find tags for texts.

Because, for now, our service is free to use and OpenAI API costs money, \
we politely ask you to set up your own OpenAI API key.

Here's how your key will be used:

- Your key will be used only to process your feeds. We will not use it for any other purposes.
- You can establish a limit on the maximum number of tokens that can be used in a month. \
This allows you to regulate your monthly spendings on the OpenAI API.
- If multiple users are subscribed to a single feed, we'll use a key with fewer usages in the current month.
- If a user who lacks a key is subscribed to a feed and the feed's news already have tags, \
the user will see these tags.
- You can find API key usage statistics at this page.

The more users set up the key, the cheaper it will be for everyone.
"""

openai_max_token_cost = decimal.Decimal("0.004")
openai_max_token_cost_n = 1000
openai_max_spendings = decimal.Decimal("10.00")

description_openai_max_tokens_in_month = f"""
Tokens are the currency of the OpenAI API world. The more tokens you use, the more you've gotta pay.

The default limit is calculated based on an estimation that should prevent your monthly spending \
from exceeding ${openai_max_spendings}. However, this figure is merely a projection and actual usage may vary.

"""


description_openai_process_entries_not_older_than = """
Some feeds keep all their news, regardless of their age. If you subscribe to such a feed, \
it may eat a lot of your OpenAI tokens.

To prevent this, we allow limiting the age of news to be processed with your OpenAI key.

If you want to help us and tag everything, you can set this value to a big number, like 100500.
"""

description_openai_allow_use_key_for_collections = """
Enable if you want to help new users by providing good tags for feeds in standard collections. \
If you enable this your OpenAI key will be used for feeds in collections the same way as for your feeds."
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
        key=UserSetting.openai_max_tokens_in_month,
        name="OpenAI max tokens in month",
        type=types.Integer(),
        default=int(openai_max_spendings / openai_max_token_cost * openai_max_token_cost_n),
        description=description_openai_max_tokens_in_month,
    )
)

user_settings.add(
    Value(
        key=UserSetting.openai_hide_message_about_setting_up_key,
        name="Hide message about setting up OpenAI API key",
        type=types.Boolean(),
        default=False,
        description=None,
    )
)

user_settings.add(
    Value(
        key=UserSetting.openai_process_entries_not_older_than,
        name="Use OpenAI key only for entries not older than N days",
        type=types.Integer(),
        default=3,
        description=description_openai_process_entries_not_older_than,
    )
)

user_settings.add(
    Value(
        key=UserSetting.openai_allow_use_key_for_collections,
        name="Allow using OpenAI key for feeds in standard collections",
        type=types.Boolean(),
        default=False,
        description=description_openai_allow_use_key_for_collections,
    )
)
