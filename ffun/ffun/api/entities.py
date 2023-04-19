import datetime
import enum
import uuid
from typing import Iterable

import pydantic
from ffun.core import api
from ffun.feeds import entities as f_entities
from ffun.library import entities as l_entities
from ffun.markers import entities as m_entities
from ffun.scores import entities as s_entities


class Marker(str, enum.Enum):
    read = 'read'

    @classmethod
    def from_internal(cls, marker: m_entities.Marker) -> 'Marker':
        return cls(marker.name)


class Feed(api.Base):
    id: uuid.UUID
    url: str
    state: str
    lastError: str|None = None
    loadedAt: datetime.datetime|None

    @classmethod
    def from_internal(cls, feed: f_entities.Feed) -> 'Feed':
        return cls(
            id=feed.id,
            url=feed.url,
            state=feed.state.name,
            lastError=feed.last_error.name if feed.last_error else None,
            loadedAt=feed.loaded_at,
        )


class Entry(api.Base):
    id: uuid.UUID
    feed_id: uuid.UUID
    title: str
    url: str
    tags: list[str]
    markers: list[Marker] = []
    score: int
    publishedAt: datetime.datetime
    catalogedAt: datetime.datetime
    body: str|None = None

    @classmethod
    def from_internal(cls,
                      entry: l_entities.Entry,
                      tags: Iterable[str],
                      markers: Iterable[Marker],
                      score: int,
                      with_body: bool = False) -> 'Entry':
        return cls(
            id=entry.id,
            feed_id=entry.feed_id,
            title=entry.title,
            url=entry.external_url,
            tags=list(tags),
            markers=list(markers),
            score=score,
            publishedAt=entry.published_at,
            catalogedAt=entry.cataloged_at,
            body=entry.body if with_body else None
        )


class Rule(api.Base):
    id: uuid.UUID
    tags: list[str]
    score: int
    createdAt: datetime.datetime

    @classmethod
    def from_internal(cls, rule: s_entities.Rule, tags_mapping: dict[int, str]) -> 'Rule':
        return cls(
            id=rule.id,
            tags={tags_mapping[tag_id] for tag_id in rule.tags},
            score=rule.score,
            createdAt=rule.created_at,
        )


##################
# Request/Response
##################

class GetFeedsRequest(api.APIRequest):
    pass


class GetFeedsResponse(api.APISuccess):
    feeds: list[Feed]


class GetLastEntriesRequest(api.APIRequest):
    period: datetime.timedelta|None = None

    @pydantic.validator('period')
    def validate_period(cls, v):
        if v is not None and v.total_seconds() < 0:
            raise ValueError('period must be positive')
        return v


class GetLastEntriesResponse(api.APISuccess):
    entries: list[Entry]


class GetEntriesByIdsRequest(api.APIRequest):
    ids: list[uuid.UUID]


class GetEntriesByIdsResponse(api.APISuccess):
    entries: list[Entry]


class CreateRuleRequest(api.APIRequest):
    tags: list[str]
    score: int


class CreateRuleResponse(api.APISuccess):
    pass


class DeleteRuleRequest(api.APIRequest):
    id: uuid.UUID


class DeleteRuleResponse(api.APISuccess):
    pass


class UpdateRuleRequest(api.APIRequest):
    id: uuid.UUID
    tags: list[str]
    score: int


class UpdateRuleResponse(api.APISuccess):
    pass


class GetRulesRequest(api.APIRequest):
    pass


class GetRulesResponse(api.APISuccess):
    rules: list[Rule]


class GetScoreDetailsRequest(api.APIRequest):
    entryId: uuid.UUID


class GetScoreDetailsResponse(api.APISuccess):
    rules: list[Rule]


class SetMarkerRequest(api.APIRequest):
    entryId: uuid.UUID
    marker: Marker


class RemoveMarkerRequest(api.APIRequest):
    entryId: uuid.UUID
    marker: Marker
