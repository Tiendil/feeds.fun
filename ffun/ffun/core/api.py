import enum
from typing import Any

import pydantic

from ffun.core.entities import BaseEntity


class APIStatuses(str, enum.Enum):
    success = "success"
    error = "error"


class MessageType(str, enum.Enum):
    info = "info"
    warning = "warning"
    error = "error"


class Message(BaseEntity):
    type: MessageType
    code: str
    message: str


class APIRequest(BaseEntity):
    model_config = pydantic.ConfigDict(title="Request Body")


class APISuccess(BaseEntity):
    status: APIStatuses = APIStatuses.success
    messages: list[Message] = pydantic.Field(default_factory=list)

    model_config = pydantic.ConfigDict(title="Response Body")


# TODO: refactor to allow list of messages?
class APIError(BaseEntity):
    status: APIStatuses = APIStatuses.error
    code: str
    message: str = "Unknown error"
    data: dict[str, Any] | None = None

    model_config = pydantic.ConfigDict(title="API Error")
