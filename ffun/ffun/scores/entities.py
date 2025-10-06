import datetime

from ffun.core.entities import BaseEntity
from ffun.domain.entities import RuleId, TagId, UserId


class Rule(BaseEntity):
    id: RuleId
    user_id: UserId

    required_tags: set[TagId]
    excluded_tags: set[TagId]
    score: int

    created_at: datetime.datetime
    updated_at: datetime.datetime

    # TODO: test
    # TODO: detect circular replacements
    # TODO: detect when the same tag in both required and excluded after replacement
    def replace_tags(self, replacements: dict[TagId, TagId]) -> "Rule":
        new_required_tags = {replacements.get(tag, tag) for tag in self.required_tags}
        new_excluded_tags = {replacements.get(tag, tag) for tag in self.excluded_tags}

        return self.replace(required_tags=new_required_tags, excluded_tags=new_excluded_tags)

    def soft_compare(self, user_id: UserId, required_tags: set[TagId], excluded_tags: set[TagId], score: int) -> bool:
        return (
            self.user_id == user_id
            and self.required_tags == required_tags
            and self.excluded_tags == excluded_tags
            and self.score == score
        )
