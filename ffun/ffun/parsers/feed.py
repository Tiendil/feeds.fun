import datetime
import io
import time
from typing import Iterable, Mapping, Protocol, cast

import feedparser
from feedparser.sanitizer import _HTMLSanitizer

from ffun.core import logging, utils
from ffun.domain import urls
from ffun.domain.entities import AbsoluteUrl, FeedUrl, SourceUid, UnknownUrl
from ffun.integrations.settings import settings as i_settings
from ffun.library.entities import Reference, ReferenceKind
from ffun.library.utils import merge_references_list
from ffun.parsers import errors
from ffun.parsers.entities import EntryInfo, FeedInfo

logger = logging.get_module_logger()


# IMPORTANT: For now we sanitize iframes on the frontend side.
#            Later we'll move purification to the backend (see https://github.com/Tiendil/feeds.fun/issues/514).
_HTMLSanitizer.acceptable_elements.add("iframe")  # type: ignore[misc]


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


def _extract_external_url(entry: Mapping[str, object], original_url: FeedUrl) -> AbsoluteUrl:
    url = entry.get("link")

    if not isinstance(url, str):
        raise errors.CanNotExtractExternalUrl()

    adjusted_url = urls.adjust_external_url(UnknownUrl(url), original_url)

    if adjusted_url is None:
        raise errors.CanNotExtractExternalUrl()

    return adjusted_url


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


def _media_type_to_kind(media_type: str | None) -> ReferenceKind:  # noqa: CCR001
    if media_type is None:
        return ReferenceKind.unknown

    normalized_media_type = media_type.split(";", 1)[0].strip().lower()

    if normalized_media_type.startswith("image/"):
        return ReferenceKind.image

    if normalized_media_type.startswith("audio/"):
        return ReferenceKind.audio

    if normalized_media_type.startswith("video/"):
        return ReferenceKind.video

    if normalized_media_type in {"text/html", "application/xhtml+xml"}:
        return ReferenceKind.page

    if normalized_media_type in {"application/x-shockwave-flash"}:
        return ReferenceKind.video

    if normalized_media_type.startswith("text/") or normalized_media_type.startswith("application/"):
        return ReferenceKind.document

    return ReferenceKind.unknown


def _create_reference(  # noqa: PLR0913, CFQ002
    kind: ReferenceKind,
    url: str | None,
    original_url: FeedUrl,
    title: str | None = None,
    mime_type: str | None = None,
    width: str | int | None = None,
    height: str | int | None = None,
    duration: str | int | float | None = None,
    size: str | int | None = None,
    extra: dict[str, int | float | str | None] | None = None,
) -> Reference | None:
    if url is None:
        return None

    try:
        adjusted_url = urls.adjust_external_url(UnknownUrl(url), original_url)

        if adjusted_url is None:
            return None

        return Reference(
            kind=kind,
            url=adjusted_url,
            title=title,
            mime_type=mime_type,
            width=int(width) if width is not None else None,
            height=int(height) if height is not None else None,
            duration=datetime.timedelta(seconds=float(duration)) if duration is not None else None,
            size=int(size) if size is not None else None,
            extra=extra,
        )
    except Exception:
        return None


def _reference_kind_from_link(rel: str | None, media_type: str | None) -> ReferenceKind:
    if rel == "replies":
        return ReferenceKind.comments

    kind = _media_type_to_kind(media_type)

    if kind != ReferenceKind.unknown:
        return kind

    if rel in {"alternate", "related", "via"}:
        return ReferenceKind.page

    return ReferenceKind.unknown


def _extract_link_reference(
    raw_link: object,
    original_url: FeedUrl,
) -> Reference | None:
    assert isinstance(raw_link, Mapping)

    reference = _create_reference(
        kind=_reference_kind_from_link(raw_link.get("rel"), raw_link.get("type")),
        url=cast(str | None, raw_link.get("href")),
        original_url=original_url,
        title=raw_link.get("title"),
        mime_type=raw_link.get("type"),
    )

    if reference is None:
        return None

    return reference


def _extract_media_reference(
    raw_media_entry: object,
    original_url: FeedUrl,
    default_kind: ReferenceKind,
) -> Reference | None:
    assert isinstance(raw_media_entry, Mapping)

    kind = _media_type_to_kind(raw_media_entry.get("type"))

    if kind == ReferenceKind.unknown:
        kind = default_kind

    return _create_reference(
        kind=kind,
        url=cast(str | None, raw_media_entry.get("url")),
        original_url=original_url,
        title=raw_media_entry.get("title"),
        mime_type=raw_media_entry.get("type"),
        width=raw_media_entry.get("width"),
        height=raw_media_entry.get("height"),
        duration=raw_media_entry.get("duration"),
        size=raw_media_entry.get("filesize", raw_media_entry.get("file_size")),
    )


def _extract_media_content_reference(raw_media_entry: object, original_url: FeedUrl) -> Reference | None:
    return _extract_media_reference(
        raw_media_entry=raw_media_entry,
        original_url=original_url,
        default_kind=ReferenceKind.unknown,
    )


def _extract_media_thumbnail_reference(raw_media_entry: object, original_url: FeedUrl) -> Reference | None:
    return _extract_media_reference(
        raw_media_entry=raw_media_entry,
        original_url=original_url,
        default_kind=ReferenceKind.image,
    )


def _extract_comments_reference(raw_comments_url: object, original_url: FeedUrl) -> Reference | None:
    return _create_reference(
        kind=ReferenceKind.comments,
        url=cast(str | None, raw_comments_url),
        original_url=original_url,
        title="Comments",
    )


def _extract_author_reference(raw_author: object, original_url: FeedUrl) -> Reference | None:
    if not isinstance(raw_author, Mapping):
        return None

    return _create_reference(
        kind=ReferenceKind.author,
        url=cast(str | None, raw_author.get("href")),
        original_url=original_url,
        title=cast(str | None, raw_author.get("name")),
    )


def _extract_enclosure_reference(raw_enclosure: object, original_url: FeedUrl) -> Reference | None:
    assert isinstance(raw_enclosure, Mapping)

    return _create_reference(
        kind=_media_type_to_kind(raw_enclosure.get("type")),
        url=cast(str | None, raw_enclosure.get("href")),
        original_url=original_url,
        title=raw_enclosure.get("title"),
        mime_type=raw_enclosure.get("type"),
        size=raw_enclosure.get("length"),
    )


def _extract_raw_reference_items(entry: Mapping[str, object], key: str) -> list[object]:
    items = entry.get(key)

    if items is None:
        return []

    assert isinstance(items, list)
    return items


def _extract_references_raw(
    entry: Mapping[str, object], original_url: FeedUrl, primary_url: AbsoluteUrl
) -> list[Reference]:  # noqa: CCR001
    references: list[Reference | None] = []

    for raw_link in _extract_raw_reference_items(entry, "links"):
        references.append(_extract_link_reference(raw_link, original_url))

    for raw_enclosure in _extract_raw_reference_items(entry, "enclosures"):
        references.append(_extract_enclosure_reference(raw_enclosure, original_url))

    for raw_media_entry in _extract_raw_reference_items(entry, "media_content"):
        references.append(_extract_media_content_reference(raw_media_entry, original_url))

    for raw_media_entry in _extract_raw_reference_items(entry, "media_thumbnail"):
        references.append(_extract_media_thumbnail_reference(raw_media_entry, original_url))

    references.append(_extract_comments_reference(entry.get("comments"), original_url))

    references.append(_extract_author_reference(entry.get("author_detail"), original_url))

    for raw_contributor in _extract_raw_reference_items(entry, "contributors"):
        references.append(_extract_author_reference(raw_contributor, original_url))

    return [reference for reference in references if reference is not None and reference.url != primary_url]


def _extract_references(
    entry: Mapping[str, object], original_url: FeedUrl, primary_url: AbsoluteUrl
) -> list[Reference]:
    references = _extract_references_raw(entry, original_url, primary_url)
    return merge_references_list(references)


def _parse_entry_strict(raw_entry: Mapping[str, object], original_url: FeedUrl, source: SourceUid) -> EntryInfo:
    # TODO: remove all tags from title
    # TODO: extract tags from <category> tag
    published_at = _extract_published_at(raw_entry)
    external_url = _extract_external_url(raw_entry, original_url)

    entry = EntryInfo(
        title=raw_entry.get("title", ""),  # type: ignore
        body=_extract_body(raw_entry),
        external_id=_extract_external_id(raw_entry),
        external_url=external_url,
        external_tags=_parse_tags(raw_entry.get("tags", ())),  # type: ignore
        published_at=published_at,
        references=_extract_references(raw_entry, original_url, external_url),
    )

    integration = i_settings.get_integration_by_source(source)

    if integration is None:
        return entry

    return integration.plugin_instance.postprocess_entry(entry)


def parse_entry(raw_entry: Mapping[str, object], original_url: FeedUrl, source: SourceUid) -> EntryInfo | None:
    if _should_skip(raw_entry):
        return None

    try:
        return _parse_entry_strict(raw_entry, original_url, source)
    except errors.CanNotExtractExternalUrl:
        logger.warning("can_not_extract_external_url_from_feed_entry", entry=raw_entry, original_url=original_url)
    except Exception:
        logger.exception("error_while_parsing_feed_entry", entry=raw_entry, original_url=original_url)

    return None


class Channel(Protocol):
    feed: Mapping[str, object]
    entries: list[Mapping[str, object]]
    version: str


def _parse_stream(input_stream: io.IOBase) -> Channel:
    return feedparser.parse(input_stream)  # type: ignore


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


def parse_feed(content: str, original_url: FeedUrl, source: SourceUid) -> FeedInfo | None:  # noqa: CCR001
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
        parsed_entry = parse_entry(entry, original_url, source)

        if parsed_entry is None:
            continue

        feed_info.entries.append(parsed_entry)

    return feed_info
