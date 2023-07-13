import datetime
import uuid

import pydantic


class FeedLink(pydantic.BaseModel):
    user_id: uuid.UUID
    feed_id: uuid.UUID
    created_at: datetime.datetime
