import enum
from typing import Any

import pydantic

from ffun.core.entities import BaseEntity


class APIStatuses(str, enum.Enum):
    success = "success"
    error = "error"


class APIRequest(BaseEntity):
    model_config = pydantic.ConfigDict(title="Request Body")


class APISuccess(BaseEntity):
    status: APIStatuses = APIStatuses.success

    model_config = pydantic.ConfigDict(title="Response Body")


class APIError(BaseEntity):
    status: APIStatuses = APIStatuses.error
    code: str
    message: str = "Unknown error"
    data: dict[str, Any] | None = None

    model_config = pydantic.ConfigDict(title="API Error")
