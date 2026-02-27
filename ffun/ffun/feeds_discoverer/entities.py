import enum
from collections.abc import Awaitable
from typing import Protocol, Union, runtime_checkable

import pydantic
from bs4 import BeautifulSoup

from ffun.core.entities import BaseEntity
from ffun.domain.entities import AbsoluteUrl, FeedUrl, UnknownUrl
from ffun.parsers import entities as p_entities

DiscoverResult = tuple["Context", Union[None, "Result"]]


@runtime_checkable
class Discoverer(Protocol):
    def __call__(self, context: "Context") -> Awaitable[DiscoverResult]:
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
    host: str | None = None
    content: str | None = None
    soup: BeautifulSoup | None = None
    depth: int = 1
    candidate_urls: set[AbsoluteUrl] = pydantic.Field(default_factory=set)
    discoverers: list[Discoverer] = pydantic.Field(default_factory=list)

    model_config = pydantic.ConfigDict(arbitrary_types_allowed=True)


class Result(BaseEntity):
    feeds: list[p_entities.FeedInfo]
    status: Status
