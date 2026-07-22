from typing import Self, TypeVar, cast

import pydantic
from pydantic_core import core_schema

BASE_ENTITY = TypeVar("BASE_ENTITY", bound="BaseEntity")


class NonEmptyString(str):
    __slots__ = ()

    def __new__(cls, value: str) -> Self:
        value = value.strip()

        if not value:
            raise ValueError(f"{cls.__name__} must not be empty")

        return super().__new__(cls, value)

    @classmethod
    def __get_pydantic_core_schema__(
        cls,
        _source_type: object,
        handler: pydantic.GetCoreSchemaHandler,
    ) -> core_schema.CoreSchema:
        return cast(
            core_schema.CoreSchema,
            core_schema.no_info_after_validator_function(cls, handler(str)),
        )


class BaseEntity(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(
        str_strip_whitespace=True,
        validate_default=True,
        extra="forbid",
        frozen=True,
        validate_assignment=True,
        from_attributes=False,
    )

    def replace(self: BASE_ENTITY, **kwargs: object) -> BASE_ENTITY:
        return self.model_copy(update=kwargs, deep=True)
