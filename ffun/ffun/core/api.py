import enum
from typing import Any

import pydantic


class Base(pydantic.BaseModel):
    class Config:
        anystr_strip_whitespace = True
        validate_all = True
        extra = "forbid"
        allow_mutation = False
        frozen = True
        validate_assignment = True
        orm_mode = False
        underscore_attrs_are_private = True


class APIStatuses(str, enum.Enum):
    success = "success"
    error = "error"


class APIRequest(Base):
    class Config(Base.Config):
        title = "Request Body"


class APISuccess(Base):
    status: APIStatuses = APIStatuses.success

    class Config(Base.Config):
        title = "Response Body"


class APIError(Base):
    status: APIStatuses = APIStatuses.error
    code: str
    message: str | None
    data: dict[str, Any] | None = None

    class Config(Base.Config):
        title = "API Error"
