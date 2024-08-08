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

    actual_must_have_found: int
    actual_must_have_missing: list[str]
    actual_should_have_found: int

    last_must_have_found: int
    last_must_have_missing: list[str]
    last_should_have_found: int

    must_have_total: int
    should_have_total: int

    @pydantic.field_validator("actual_must_have_missing")
    @classmethod
    def sort_actual_must_have_missing_tags(cls, v: str) -> str:
        return list(sorted(v))

    @pydantic.field_validator("last_must_have_missing")
    @classmethod
    def sort_last_must_have_missing_tags(cls, v: str) -> str:
        return list(sorted(v))
