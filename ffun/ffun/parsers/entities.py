import datetime
from typing import Any

import pydantic

from ffun.domain.entities import AbsoluteUrl


class EntryInfo(pydantic.BaseModel):
    title: str
    body: str
    external_id: str
    external_url: AbsoluteUrl | None
    external_tags: set[str]
    published_at: datetime.datetime

    def log_info(self) -> dict[str, Any]:
        return {"title": self.title, "external_url": self.external_url}


class FeedInfo(pydantic.BaseModel):
    url: AbsoluteUrl
    title: str
    description: str

    entries: list[EntryInfo]

    def log_info(self) -> dict[str, Any]:
        return {"title": self.title, "url": self.url}
