from typing import Literal

from ffun.core.entities import BaseEntity
from ffun.domain.entities import EntryId


class NewsLinkOpened(BaseEntity):
    name: Literal["news_link_opened"]
    entry_id: EntryId


class NewsBodyOpened(BaseEntity):
    name: Literal["news_body_opened"]
    entry_id: EntryId


class SocialLinkClicked(BaseEntity):
    name: Literal["social_link_clicked"]
    link_type: Literal["api", "blog", "reddit", "discord", "github"]


class TagFilterStateChanged(BaseEntity):
    name: Literal["tag_filter_state_changed"]
    tag: str
    from_state: Literal["required", "excluded", "none"]
    to_state: Literal["required", "excluded", "none"]
    source: Literal["news_tags_filter", "rules_tags_filter", "entry_record", "rule_record"]


Event = NewsLinkOpened | NewsBodyOpened | SocialLinkClicked | TagFilterStateChanged
