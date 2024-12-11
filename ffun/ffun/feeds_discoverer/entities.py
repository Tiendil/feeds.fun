import datetime
import enum
from typing import Any, Protocol
import pydantic

from ffun.core import utils
from ffun.core.entities import BaseEntity
from ffun.domain.entities import EntryId, FeedId, SourceId
from ffun.parsers import entities as p_entities


# async def _discover_extract_feeds_from_anchors(context: Context) -> tuple[Context, Result | None]:

class Discoverer(Protocol):
    async def __call__(self, context: 'Context') -> tuple['Context', 'Result' | None]:
        pass


class Status(enum.StrEnum):
    feeds_found = "feeds_found"
    incorrect_url = "incorrect_url"
    no_content_at_url = "no_content_at_url"
    not_html = "not_html"
    no_feeds_found = "no_feeds_found"


class Context:
    raw_url: str
    url: str | None
    content: str | None
    soup: Any | None
    depth: int
    candidate_urls: list[str] = pydantic.Field(default_factory=list)
    discoverers: list[Discoverer] = pydantic.Field(default_factory=list)

    model_config = pydantic.ConfigDict(frozen=False)


class Result:
    feeds: list[p_entities.FeedInfo]
    status: Status
