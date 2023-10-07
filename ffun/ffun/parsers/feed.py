import datetime
from typing import Any, Iterable

import feedparser
from furl import furl

from ffun.core import logging
from ffun.parsers.entities import EntryInfo, FeedInfo

logger = logging.get_module_logger()


def _parse_tags(tags: Iterable[dict[str, Any]]) -> set[str]:
    result = set()

    for tag in tags:
        if tag.get("label") is not None:
            result.add(tag["label"])

        elif tag.get("term") is not None:
            result.add(tag["term"])

    return result


def _should_skip(entry: Any) -> bool:
    if entry.get("link") is None:
        logger.warning("feed_does_not_has_link_field")
        return True

    return False


def _extract_published_at(entry: Any) -> datetime.datetime:
    published_at = entry.get("published_parsed")

    if published_at is not None:
        return datetime.datetime(*published_at[:6])

    return datetime.datetime.now()


# not the best solution, but it works for now
# TODO: we should use more formal way to detect uniqueness of entry
# TODO: external id must be normalized
def _extract_external_id(entry: Any) -> str:
    return entry.get("link")


# is required for correct parsing by furl
# will be removed before returning result
def _fake_schema_for_url(url: str) -> str:
    if '//' not in url and url[0] != '/' and ('.' in url.split('/')[0]):
        return f'//{url}'

    return url


def _normalize_external_url(url: str, original_url: str) -> str:
    url = _fake_schema_for_url(url)
    original_url = _fake_schema_for_url(original_url)

    external_url = furl(url)

    f_original_url = furl(original_url)

    if not external_url.scheme:
        external_url.set(scheme=f_original_url.scheme)

    if not external_url.netloc:
        external_url.set(netloc=f_original_url.netloc)

    result_url = str(external_url)

    if result_url.startswith('//'):
        result_url = result_url[2:]

    return result_url


def _extract_external_url(entry: Any, original_url: str) -> str:
    url = entry.get("link")

    return _normalize_external_url(url, original_url)


def parse_feed(content: str, original_url: str) -> FeedInfo | None:
    channel = feedparser.parse(content)

    if getattr(channel, "version", "") == "" and not channel.entries:
        return None

    feed_info = FeedInfo(
        url=original_url,
        title=channel.feed.get("title", ""),
        description=channel.feed.get("description", ""),
        entries=[],
    )

    for entry in channel.entries:
        # TODO: remove all tags from title
        # TODO: extract tags from <category> tag

        if _should_skip(entry):
            continue

        published_at = _extract_published_at(entry)

        feed_info.entries.append(
            EntryInfo(
                title=entry.get("title", ""),
                body=entry.get("description", ""),
                external_id=_extract_external_id(entry),
                external_url=_extract_external_url(entry, original_url),
                external_tags=_parse_tags(entry.get("tags", ())),
                published_at=published_at,
            )
        )

    return feed_info
