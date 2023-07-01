
import enum

from ffun.user_settings import types
from ffun.user_settings.values import Value, user_settings


class UserSetting(int, enum.Enum):
    openai_api_key = 1
    openai_max_tokens_in_month = 2


user_settings.add(Value(key=UserSetting.openai_api_key,
                        name="OpenAI API Key",
                        type=types.Secret()))

user_settings.add(Value(key=UserSetting.openai_max_tokens_in_month,
                        name="OpenAI Max Tokens in Month",
                        type=types.Integer()))
