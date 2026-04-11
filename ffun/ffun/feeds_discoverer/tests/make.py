
from typing import TypedDict, Unpack

import httpx
import pytest
from pytest_mock import MockerFixture
from respx.router import MockRouter

from ffun.domain.entities import AbsoluteUrl, FeedUrl, UnknownUrl
from ffun.domain.urls import str_to_feed_url, url_to_host
from ffun.feeds_discoverer.domain import (
    _VISITED_URLS,
    _discover_adjust_url,
    _discover_check_candidate_links,
    _discover_check_parent_urls,
    _discover_create_soup,
    _discover_extract_feed_info,
    _discover_extract_feeds_for_plugins,
    _discover_extract_feeds_from_anchors,
    _discover_extract_feeds_from_links,
    _discover_load_url,
    _discover_stop_recursion,
    _discoverers,
    discover,
    visited_cache,
)
from ffun.feeds_discoverer.entities import Context, Discoverer, Result, Status


class _ContextParams(TypedDict, total=False):
    content: str | None
    depth: int
    candidate_urls: set[AbsoluteUrl]
    discoverers: list[Discoverer]


def context(url: str, **kwargs: Unpack[_ContextParams]) -> Context:
    prepered_url = str_to_feed_url(url)
    return Context(raw_url=UnknownUrl(url), url=prepered_url, host=url_to_host(prepered_url), **kwargs)
