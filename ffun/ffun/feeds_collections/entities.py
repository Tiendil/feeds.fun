import enum
import uuid
from typing import Any, NewType

from ffun.core.entities import BaseEntity


class FeedInfo(BaseEntity):
    url: str

    # Some feeds define title and description in their data
    # But, currently, it looks more convenient to define them here
    # So, we can describe feeds in a consistent way resistent to problems on the feed side
    title: str
    description: str


CollectionId = NewType("CollectionId", uuid.UUID)


class Collection(BaseEntity):
    id: CollectionId
    name: str
    description: str
    feeds: list[FeedInfo]
