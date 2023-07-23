import datetime
import enum
import uuid
from typing import Any

import pydantic

from ffun.core import utils


class ProcessedState(int, enum.Enum):
    success = 1
    error = 2
    retry_later = 3


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

    @property
    def age(self) -> datetime.timedelta:
        return utils.now() - self.published_at

    def log_info(self) -> dict[str, Any]:
        return {"id": self.id, "feed_id": self.feed_id, "title": self.title, "external_url": self.external_url}
