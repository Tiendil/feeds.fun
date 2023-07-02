import decimal
import enum

from ffun.user_settings import types
from ffun.user_settings.values import Value, user_settings


class Resource(int, enum.Enum):
    openai_tokens = 1
