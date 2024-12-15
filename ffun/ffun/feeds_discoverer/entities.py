import enum
from typing import Any, Protocol, Union

import pydantic

from ffun.core.entities import BaseEntity
from ffun.domain.entities import AbsoluteUrl, FeedUrl, UnknownUrl
from ffun.parsers import entities as p_entities


class Discoverer(Protocol):
    async def __call__(self, context: "Context") -> tuple["Context", Union[None, "Result"]]:
        pass


class Status(enum.StrEnum):
    feeds_found = "feeds_found"
    incorrect_url = "incorrect_url"
    cannot_access_url = "cannot_access_url"
    not_html = "not_html"
    no_feeds_found = "no_feeds_found"


class Context(BaseEntity):
    raw_url: UnknownUrl
    url: FeedUrl | None = None
    content: str | None = None
    soup: Any | None = None
    depth: int = 1
    candidate_urls: set[AbsoluteUrl] = pydantic.Field(default_factory=set)
    discoverers: list[Any] = pydantic.Field(default_factory=list)

    model_config = pydantic.ConfigDict(arbitrary_types_allowed=True)


class Result(BaseEntity):
    feeds: list[p_entities.FeedInfo]
    status: Status
