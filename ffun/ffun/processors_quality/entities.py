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
