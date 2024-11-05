from ffun.core.entities import BaseEntity
from ffun.domain.entities import EntryId

from typing import Literal


class NewsLinkOpened(BaseEntity):
    name: Literal["news_link_opened"]
    entry_id: EntryId


class NewsBodyOpened(BaseEntity):
    name: Literal["news_body_opened"]
    entry_id: EntryId


Event = NewsLinkOpened | NewsBodyOpened
