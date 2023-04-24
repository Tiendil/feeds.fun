
import datetime
import uuid

import pydantic


class Entry(pydantic.BaseModel):
    id: uuid.UUID
    feed_id: uuid.UUID
    title: str
    body: str
    external_id: str
    external_url: str
    external_tags: set[str]
    published_at: datetime.datetime
    cataloged_at: datetime.datetime

    def log_info(self):
        return {'id': self.id,
                'feed_id': self.feed_id,
                'title': self.title,
                'external_url': self.external_url}
