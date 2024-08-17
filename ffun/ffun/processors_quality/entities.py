import datetime

import pydantic

from ffun.core.entities import BaseEntity


class ExpectedTags(BaseEntity):
    must_have: set[str]
    should_have: set[str]

    @pydantic.model_validator(mode="after")
    def tags_must_not_intersect(self) -> "ExpectedTags":
        if self.must_have & self.should_have:
            raise ValueError(f"Tags must not intersect, common tags: {self.must_have & self.should_have}")

        return self


class ProcessorResult(BaseEntity):
    tags: list[str]
    created_at: datetime.datetime


class ProcessorResultDiff(BaseEntity):
    entry_id: int

    actual_total: int
    actual_must_have_found: int
    actual_must_have_missing: list[str]
    actual_should_have_found: int
    actual_has_and_last_not: list[str]

    last_total: int
    last_must_have_found: int
    last_must_have_missing: list[str]
    last_should_have_found: int
    last_has_and_actual_not: list[str]

    must_have_total: int
    should_have_total: int

    @pydantic.field_validator("actual_must_have_missing")
    @classmethod
    def sort_actual_must_have_missing_tags(cls, v: list[str]) -> list[str]:
        return list(sorted(v))

    @pydantic.field_validator("last_must_have_missing")
    @classmethod
    def sort_last_must_have_missing_tags(cls, v: list[str]) -> list[str]:
        return list(sorted(v))

    @pydantic.field_validator("actual_has_and_last_not")
    @classmethod
    def sort_actual_has_and_last_not_tags(cls, v: list[str]) -> list[str]:
        return list(sorted(v))

    @pydantic.field_validator("last_has_and_actual_not")
    @classmethod
    def sort_last_has_and_actual_not_tags(cls, v: list[str]) -> list[str]:
        return list(sorted(v))


class Attribution(BaseEntity):
    title: str = pydantic.Field(..., min_length=1)
    authors: list[str] = pydantic.Field(..., min_items=1)  # type: ignore
    link: str = pydantic.Field(..., min_length=1)
    license: str = pydantic.Field(..., min_length=1)
