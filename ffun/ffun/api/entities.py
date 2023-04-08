import datetime
import uuid
from typing import Iterable

import pydantic
from ffun.core import api
from ffun.feeds import entities as f_entities
from ffun.library import entities as l_entities


class Feed(api.Base):
    id: uuid.UUID
    url: str
    loadedAt: datetime.datetime

    @classmethod
    def from_internal(cls, feed: f_entities.Feed) -> 'Feed':
        return cls(
            id=feed.id,
            url=feed.url,
            loadedAt=feed.loaded_at,
        )


class Entry(api.Base):
    id: uuid.UUID
    feed_id: uuid.UUID
    title: str
    url: str
    tags: list[str]
    score: int
    publishedAt: datetime.datetime
    catalogedAt: datetime.datetime

    @classmethod
    def from_internal(cls,
                      entry: l_entities.Entry,
                      tags: Iterable[str],
                      score: int) -> 'Entry':
        return cls(
            id=entry.id,
            feed_id=entry.feed_id,
            title=entry.title,
            url=entry.external_url,
            tags=list(tags),
            score=score,
            publishedAt=entry.published_at,
            catalogedAt=entry.cataloged_at,
        )


##################
# Request/Response
##################

class GetFeedsRequest(api.APIRequest):
    pass


class GetFeedsResponse(api.APISuccess):
    feeds: list[Feed]


class GetEntriesRequest(api.APIRequest):
    period: datetime.timedelta|None = None

    @pydantic.validator('period')
    def validate_period(cls, v):
        if v is not None and v.total_seconds() < 0:
            raise ValueError('period must be positive')
        return v


class GetEntriesResponse(api.APISuccess):
    entries: list[Entry]
