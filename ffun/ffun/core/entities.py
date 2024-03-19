from typing import Any, TypeVar

import pydantic

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
        return self.model_copy(update=kwargs, deep=True)
