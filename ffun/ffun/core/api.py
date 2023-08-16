import enum
from typing import Any

import pydantic


class Base(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(
        str_strip_whitespace=True,
        validate_default=True,
        extra="forbid",
        frozen=True,
        validate_assignment=True,
        from_attributes=False,
    )


class APIStatuses(str, enum.Enum):
    success = "success"
    error = "error"


class APIRequest(Base):
    model_config = pydantic.ConfigDict(title="Request Body")


class APISuccess(Base):
    status: APIStatuses = APIStatuses.success

    model_config = pydantic.ConfigDict(title="Response Body")


class APIError(Base):
    status: APIStatuses = APIStatuses.error
    code: str
    message: str = "Unknown error"
    data: dict[str, Any] | None = None

    model_config = pydantic.ConfigDict(title="API Error")
