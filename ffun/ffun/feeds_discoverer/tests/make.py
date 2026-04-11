from typing import TypedDict, Unpack

from ffun.domain.entities import AbsoluteUrl, UnknownUrl
from ffun.domain.urls import str_to_feed_url, url_to_host
from ffun.feeds_discoverer.entities import Context, Discoverer


class _ContextParams(TypedDict, total=False):
    content: str | None
    depth: int
    candidate_urls: set[AbsoluteUrl]
    discoverers: list[Discoverer]


def context(url: str, **kwargs: Unpack[_ContextParams]) -> Context:
    prepered_url = str_to_feed_url(url)
    return Context(raw_url=UnknownUrl(url), url=prepered_url, host=url_to_host(prepered_url), **kwargs)
