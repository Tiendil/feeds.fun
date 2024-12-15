import datetime
from typing import Any, Iterable

import feedparser

from ffun.core import logging
from ffun.domain import urls
from ffun.domain.entities import AbsoluteUrl, FeedUrl
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
    return entry.get("link")  # type: ignore


def _extract_external_url(entry: Any, original_url: FeedUrl) -> AbsoluteUrl | None:
    url = entry.get("link")

    return urls.adjust_external_url(url, original_url)


def parse_feed(content: str, original_url: FeedUrl) -> FeedInfo | None:
    channel = feedparser.parse(content)

    if getattr(channel, "version", "") == "" and not channel.entries:
        return None

    feed_info = FeedInfo(
        url=original_url,
        title=channel.feed.get("title", ""),
        description=channel.feed.get("description", ""),
        entries=[],
        uid=urls.url_to_uid(original_url),
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
