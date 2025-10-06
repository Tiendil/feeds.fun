import datetime

import pydantic

from ffun.core.entities import BaseEntity
from ffun.domain.entities import RuleId, TagId, UserId
from ffun.scores import errors


class Rule(BaseEntity):
    id: RuleId
    user_id: UserId

    required_tags: set[TagId]
    excluded_tags: set[TagId]
    score: int

    created_at: datetime.datetime
    updated_at: datetime.datetime

    def replace_tags(self, replacements: dict[TagId, TagId]) -> tuple[set[TagId], set[TagId]]:

        if set(replacements.keys()) & set(replacements.values()):
            raise errors.CircularTagReplacement()

        new_required_tags = {replacements.get(tag, tag) for tag in self.required_tags}
        new_excluded_tags = {replacements.get(tag, tag) for tag in self.excluded_tags}

        if new_required_tags & new_excluded_tags:
            raise errors.RuleTagsIntersection()

        return (new_required_tags, new_excluded_tags)

    def soft_compare(self, user_id: UserId, required_tags: set[TagId], excluded_tags: set[TagId], score: int) -> bool:
        return (
            self.user_id == user_id
            and self.required_tags == required_tags
            and self.excluded_tags == excluded_tags
            and self.score == score
        )

    @pydantic.model_validator(mode="after")
    def validate_tags(self) -> "Rule":
        if self.required_tags & self.excluded_tags:
            raise ValueError("A tag cannot be both required and excluded")

        return self
