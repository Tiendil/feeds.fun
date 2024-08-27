import datetime
import uuid

import pydantic

from ffun.feeds.entities import FeedId


class FeedLink(pydantic.BaseModel):
    user_id: uuid.UUID
    feed_id: FeedId
    created_at: datetime.datetime
