import enum
import uuid

import pydantic


class KeyStatus(str, enum.Enum):
    works = "works"
    broken = "broken"
    unknown = "unknown"


class APIKeyUsage(pydantic.BaseModel):
    user_id: uuid.UUID
    api_key: str
    used_tokens: int | None


class OpenAIAnswer(pydantic.BaseModel):
    content: str

    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
