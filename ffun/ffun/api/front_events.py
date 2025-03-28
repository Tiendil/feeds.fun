from typing import Literal

from ffun.core.entities import BaseEntity
from ffun.domain.entities import EntryId

EventsViewName = Literal["news", "rules", "public_collections"]


class NewsLinkOpened(BaseEntity):
    name: Literal["news_link_opened"]
    view: EventsViewName
    entry_id: EntryId


class NewsBodyOpened(BaseEntity):
    name: Literal["news_body_opened"]
    view: EventsViewName
    entry_id: EntryId


class SocialLinkClicked(BaseEntity):
    name: Literal["social_link_clicked"]
    view: EventsViewName
    link_type: Literal["api", "blog", "reddit", "discord", "github"]


class TagFilterStateChanged(BaseEntity):
    name: Literal["tag_filter_state_changed"]
    view: EventsViewName
    tag: str
    from_state: Literal["required", "excluded", "none"]
    to_state: Literal["required", "excluded", "none"]
    source: Literal["tags_filter", "entry_record", "rule_record"]


Event = NewsLinkOpened | NewsBodyOpened | SocialLinkClicked | TagFilterStateChanged
