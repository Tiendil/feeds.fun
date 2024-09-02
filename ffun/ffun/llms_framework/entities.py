import datetime
import enum
import uuid
import decimal

import pydantic


class Provider(enum.StrEnum):
    openai = "openai"
    google = "google"


class ModelInfo(pydantic.BaseModel):
    provider: Provider
    name: str
    max_context_size: int
    max_return_tokens: int


class KeyStatus(str, enum.Enum):
    works = "works"
    broken = "broken"
    quota = "quota"
    unknown = "unknown"


# Generally, different LLM providers can have config parameters with different names.
# But for simplicity, for now, we will use the unified config for all providers.
# We'll split it later if needed.
class LLMConfiguration(pydantic.BaseModel):
    model: str
    system: str
    max_return_tokens: int
    text_parts_intersection: int
    additional_tokens_per_message: int
    temperature: decimal.Decimal
    top_p: decimal.Decimal
    presence_penalty: decimal.Decimal
    frequency_penalty: decimal.Decimal
