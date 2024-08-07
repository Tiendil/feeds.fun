import datetime
import pydantic
import enum
import uuid
from typing import Any

from ffun.core.entities import BaseEntity


class ExpectedTags(BaseEntity):
    must_have: set[str]
    should_have: set[str]

    @pydantic.model_validator(mode='after')
    def tags_must_not_intersect(self) -> 'ExpectedTags':
        if self.must_have & self.should_have:
            raise ValueError(f'Tags must not intersect, common tags: {self.must_have & self.should_have}')

        return self


class ProcessorResult(BaseEntity):
    must_tags_found: list[str]
    must_tags_missing: list[str]

    should_tags_found: list[str]
    should_tags_missing: list[str]

    created_at: datetime.datetime

    @property
    def must_tags_total(self) -> int:
        return len(self.must_tags_found) + len(self.must_tags_missing)

    @property
    def must_tags_number(self) -> int:
        return len(self.must_tags_found)

    @property
    def should_tags_total(self) -> int:
        return len(self.should_tags_found) + len(self.should_tags_missing)

    @property
    def should_tags_number(self) -> int:
        return len(self.should_tags_found)
