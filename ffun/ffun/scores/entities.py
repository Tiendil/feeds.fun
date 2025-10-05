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
    def replace_tags(self, replacements: dict[TagId, TagId]) -> "Rule":
        new_required_tags = {replacements.get(tag, tag) for tag in self.required_tags}
        new_excluded_tags = {replacements.get(tag, tag) for tag in self.excluded_tags}

        return self.replace(required_tags=new_required_tags, excluded_tags=new_excluded_tags)
