import datetime
import io
import time
from typing import Iterable, Mapping, Protocol, cast

import feedparser

from ffun.core import logging, utils
from ffun.domain import urls
from ffun.domain.entities import AbsoluteUrl, FeedUrl, UnknownUrl
from ffun.library.entities import REFERENCE_SEMANTICS_PRIORITY, Reference, ReferenceSemantics
from ffun.parsers.entities import EntryInfo, FeedInfo

logger = logging.get_module_logger()


# Known feedparser issues:
#
# - Media groups are ignored: https://github.com/kurtmckee/feedparser/issues/195
#   On the example of YouTube feed that leads to separation of media link to the video from
#   the media link to the thumbnail => we treat them as separate entries
# - feedparser is "too smart" and may try to make an HTTP request if we pass content as a string


def _parse_tags(tags: Iterable[dict[str, str]]) -> set[str]:
    result: set[str] = set()

    for tag in tags:
        if (label := tag.get("label")) is not None:
            result.add(label)

        elif (term := tag.get("term")) is not None:
            result.add(term)

    return result


def _should_skip(entry: Mapping[str, object]) -> bool:
    if entry.get("link") is None:
        logger.warning("feed_does_not_has_link_field")
        return True

    return False


def _extract_published_at(entry: Mapping[str, object]) -> datetime.datetime:
    published_at = entry.get("published_parsed")

    if published_at is None and "updated_parsed" in entry:
        published_at = entry.get("updated_parsed")

    if published_at is None:
        return utils.now()

    try:
        parsed = datetime.datetime.fromtimestamp(time.mktime(cast(time.struct_time, published_at)))
    except ValueError:
        logger.warning("wrong_published_at_value", value=str(published_at))
        parsed = utils.now()

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=datetime.timezone.utc)

    return parsed


# not the best solution, but it works for now
# TODO: we should use more formal way to detect uniqueness of entry
# TODO: external id must be normalized
def _extract_external_id(entry: object) -> str:
    return entry.get("link")  # type: ignore


def _extract_external_url(entry: Mapping[str, object], original_url: FeedUrl) -> AbsoluteUrl | None:
    url = entry.get("link")

    assert isinstance(url, str)

    return urls.adjust_external_url(UnknownUrl(url), original_url)


def _extract_content(entry: Mapping[str, object]) -> str | None:
    contents = entry.get("content")

    if contents is None:
        return None

    assert isinstance(contents, list)
    assert len(contents) > 0
    assert all(isinstance(content, dict) for content in contents)

    result: str = contents[0].get("value")

    for content in contents[1:]:
        value: str = content.get("value")

        assert isinstance(value, str)

        if len(value) > len(result):
            result = value

    return result


def _extract_body(entry: Mapping[str, object]) -> str:
    description: object | None = entry.get("description")
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


# TODO: try to improve, maybe
def _media_type_to_semantics(media_type: str | None) -> ReferenceSemantics:  # noqa: CCR001
    if media_type is None:
        return ReferenceSemantics.unknown

    normalized_media_type = media_type.split(";", 1)[0].strip().lower()

    if normalized_media_type.startswith("image/"):
        return ReferenceSemantics.image

    if normalized_media_type.startswith("audio/"):
        return ReferenceSemantics.audio

    if normalized_media_type.startswith("video/"):
        return ReferenceSemantics.video

    if normalized_media_type in {"text/html", "application/xhtml+xml"}:
        return ReferenceSemantics.page

    if normalized_media_type in {"application/x-shockwave-flash"}:
        return ReferenceSemantics.video

    if normalized_media_type.startswith("text/") or normalized_media_type.startswith("application/"):
        return ReferenceSemantics.document

    return ReferenceSemantics.unknown


def _extract_references(entry: Mapping[str, object], original_url: FeedUrl) -> list[Reference]:
    references = []

    return references


def parse_entry(raw_entry: Mapping[str, object], original_url: FeedUrl) -> EntryInfo:
    # TODO: remove all tags from title
    # TODO: extract tags from <category> tag
    published_at = _extract_published_at(raw_entry)

    return EntryInfo(
        title=raw_entry.get("title", ""),  # type: ignore
        body=_extract_body(raw_entry),
        external_id=_extract_external_id(raw_entry),
        external_url=_extract_external_url(raw_entry, original_url),
        external_tags=_parse_tags(raw_entry.get("tags", ())),  # type: ignore
        published_at=published_at,
        references=_extract_references(raw_entry),
    )


class Channel(Protocol):
    feed: Mapping[str, object]
    entries: list[Mapping[str, object]]
    version: str


def _parse_stream(input_stream: io.IOBase) -> Channel:
    return feedparser.parse(input_stream)  # type: ignore


# TODO: tests
def parse_into_feedparser(content: str) -> Channel | None:
    try:
        # ATTENTION: feedparser is "too smart" and may try to make an HTTP request if we pass content as a string
        #            also it does not accept io.StringIO, so we have to use io.BytesIO
        input_stream = io.BytesIO(content.encode("utf-8"))
        channel = _parse_stream(input_stream)
    except Exception:
        logger.exception("error_while_parsing_feed")
        return None

    return channel


def parse_feed(content: str, original_url: FeedUrl) -> FeedInfo | None:  # noqa: CCR001
    channel = parse_into_feedparser(content)

    if channel is None:
        return None

    # do not remove `getattr` till we confirm that feedparser channel object always has version field
    if getattr(channel, "version", "") == "" and not channel.entries:  # type: ignore
        return None

    feed_info = FeedInfo(
        url=original_url,
        title=cast(str, channel.feed.get("title", "")),
        description=cast(str, channel.feed.get("description", "")),
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
