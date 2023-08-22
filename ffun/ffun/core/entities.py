import decimal
import enum
from typing import Any, TypeVar

import pydantic
from pydantic import BaseModel, Extra


BASE_ENTITY = TypeVar("BASE_ENTITY", bound="BaseEntity")


class BaseEntity(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(
        str_strip_whitespace=True,
        validate_default=True,
        extra="forbid",
        frozen=True,
        validate_assignment=True,
        from_attributes=False,
    )

    def replace(self: BASE_ENTITY, **kwargs: Any) -> BASE_ENTITY:
        data = self.model_dump()
        data |= kwargs
        return self.__class__(**data)
