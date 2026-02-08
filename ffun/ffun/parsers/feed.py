import datetime
import io
import time
from typing import Any, Iterable, cast

import feedparser

from ffun.core import logging, utils
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
        try:
            parsed = datetime.datetime.fromtimestamp(time.mktime(published_at))
        except ValueError:
            logger.warning("wrong_published_at_value", value=str(published_at))
            parsed = utils.now()

        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=datetime.timezone.utc)

        return parsed

    return utils.now()


# not the best solution, but it works for now
# TODO: we should use more formal way to detect uniqueness of entry
# TODO: external id must be normalized
def _extract_external_id(entry: Any) -> str:
    return entry.get("link")  # type: ignore


def _extract_external_url(entry: Any, original_url: FeedUrl) -> AbsoluteUrl | None:
    url = entry.get("link")

    return urls.adjust_external_url(url, original_url)


def _extract_content(entry: Any) -> str | None:
    contents = entry.get("content")

    if contents is None:
        return None

    result = contents[0].get("value")

    assert isinstance(result, str)

    for content in contents[1:]:
        value = content.get("value")

        assert isinstance(value, str)

        if len(value) > len(result):
            result = value

    return result


def _extract_body(entry: Any) -> str:
    description = entry.get("description")
    content = _extract_content(entry)

    if description is None and content is None:
        return ""

    if description is None:
        assert content is not None
        return content

    assert isinstance(description, str)

    if content is None:
        return description

    if len(content) >= len(description):
        return content

    return description


def parse_entry(raw_entry: Any, original_url: FeedUrl) -> EntryInfo:
    # TODO: remove all tags from title
    # TODO: extract tags from <category> tag
    published_at = _extract_published_at(raw_entry)

    return EntryInfo(
        title=raw_entry.get("title", ""),
        body=_extract_body(raw_entry),
        external_id=_extract_external_id(raw_entry),
        external_url=_extract_external_url(raw_entry, original_url),
        external_tags=_parse_tags(raw_entry.get("tags", ())),
        published_at=published_at,
    )


def parse_feed(content: str, original_url: FeedUrl) -> FeedInfo | None:  # noqa: CCR001
    try:
        # ATTENTION: feedparser is "too smart" and may try to make an HTTP request if we pass content as a string
        #            also it does not accept io.StringIO, so we have to use io.BytesIO
        channel = feedparser.parse(io.BytesIO(content.encode("utf-8")))
    except Exception:
        logger.exception("error_while_parsing_feed", original_url=original_url)
        return None

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
        if _should_skip(entry):
            continue

        try:
            parsed_entry = parse_entry(entry, original_url)
        except Exception:
            logger.exception("error_while_parsing_feed_entry", entry=entry, original_url=original_url)
            continue

        feed_info.entries.append(parsed_entry)

    return feed_info
