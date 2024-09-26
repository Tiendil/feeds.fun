import uuid
from typing import NewType
import pydantic
from ffun.core.entities import BaseEntity

from ffun.feeds.entities import FeedId


class FeedInfo(BaseEntity):
    model_config = pydantic.ConfigDict(frozen=False)

    url: str

    # Some feeds define title and description in their data
    # But, currently, it looks more convenient to define them here
    # So, we can describe feeds in a consistent way resistent to problems on the feed side
    title: str
    description: str

    feed_id: FeedId | None = None


CollectionId = NewType("CollectionId", uuid.UUID)


class Collection(BaseEntity):
    id: CollectionId
    gui_order: int
    name: str
    description: str
    feeds: list[FeedInfo]
