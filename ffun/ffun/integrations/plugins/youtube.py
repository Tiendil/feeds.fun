import enum
import re

import markdown  # type: ignore

from ffun.core import logging
from ffun.domain.entities import AbsoluteUrl, FeedUrl, UnknownUrl
from ffun.domain.urls import adjust_classic_relative_url, construct_f_url, normalize_classic_unknown_url
from ffun.feeds_discoverer import entities as fd_entities
from ffun.integrations.plugin import Plugin as BasePlugin
from ffun.library.entities import Reference, ReferenceSemantics
from ffun.loader import domain as lo_domain
from ffun.loader import errors as lo_errors
from ffun.parsers import entities as p_entities

_BARE_URL_RE = re.compile(r'(?<!\()(?<!<)(?<!")(?P<url>https?://[^\s<]+)')
_YOUTUBE_CHANNEL_ID_RE = re.compile(r"\bUC[a-zA-Z0-9_-]{22}\b")
_YOUTUBE_CHANNEL_PAGE_PREFIXES = ("@", "channel", "c", "user")
_YOUTUBE_VIDEO_PAGE_CHANNEL_PATTERNS = (
    re.compile(r'"videoDetails"\s*:\s*\{.*?"channelId"\s*:\s*"(?P<channel_id>UC[a-zA-Z0-9_-]{22})"', re.DOTALL),
    re.compile(r'"externalChannelId"\s*:\s*"(?P<channel_id>UC[a-zA-Z0-9_-]{22})"'),
)
_YOUTUBE_CHANNEL_PAGE_CHANNEL_PATTERNS = (
    re.compile(
        r'"channelMetadataRenderer"\s*:\s*\{.*?"externalId"\s*:\s*"(?P<channel_id>UC[a-zA-Z0-9_-]{22})"',
        re.DOTALL,
    ),
)
_YOUTUBE_PATH_PREFIXES = {"embed", "e", "live", "shorts", "v"}
# YouTube can answer channel pages with a consent interstitial instead of the real page.
# Sending SOCS=CAI opts into the non-interstitial response so we can extract channel ids.
_YOUTUBE_DISCOVERY_HEADERS = {"Cookie": "SOCS=CAI"}

logger = logging.get_module_logger()

DEFAULT_CHANNEL_FEED_URL = "https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
_YOUTUBE_ROOT_URL = normalize_classic_unknown_url(UnknownUrl("https://www.youtube.com"))

assert _YOUTUBE_ROOT_URL is not None


class YouTubePageKind(enum.StrEnum):
    non_youtube = "non_youtube"
    feed = "feed"
    video = "video"
    channel = "channel"
    other = "other"


def _autolink_bare_urls(text: str) -> str:
    def _replace(match: re.Match[str]) -> str:
        url: str = match.group("url")
        stripped_url = url.rstrip(".,!?;:")

        if stripped_url == "":
            return url

        suffix = url[len(stripped_url) :]
        return f"<{stripped_url}>{suffix}"

    return _BARE_URL_RE.sub(_replace, text)


def _is_youtube_host(hostname: str) -> bool:
    return (
        hostname == "youtu.be"
        or hostname == "youtube.com"
        or hostname == "youtube-nocookie.com"
        or hostname.endswith(".youtube.com")
        or hostname.endswith(".youtube-nocookie.com")
    )


def _is_youtube_feed_url(url: AbsoluteUrl | FeedUrl | str) -> bool:
    f_url = construct_f_url(url)

    return f_url is not None and str(f_url.path) == "/feeds/videos.xml"


def _is_youtube_video_page(
    hostname: str,
    path: str,
    path_segments: list[str],
) -> bool:
    return (
        hostname == "youtu.be"
        or path == "/watch"
        or (len(path_segments) >= 2 and path_segments[0] in _YOUTUBE_PATH_PREFIXES)
    )


def _is_youtube_channel_page(path_segments: list[str]) -> bool:
    return bool(
        path_segments and (path_segments[0].startswith("@") or path_segments[0] in _YOUTUBE_CHANNEL_PAGE_PREFIXES)
    )


def _detect_youtube_page_kind(url: AbsoluteUrl | FeedUrl | str) -> YouTubePageKind:
    f_url = construct_f_url(url)

    if f_url is None or f_url.host is None or not _is_youtube_host(f_url.host.lower()):
        return YouTubePageKind.non_youtube

    if _is_youtube_feed_url(url):
        return YouTubePageKind.feed

    path = str(f_url.path)
    path_segments = [segment for segment in f_url.path.segments if segment]

    if _is_youtube_video_page(f_url.host.lower(), path, path_segments):
        return YouTubePageKind.video

    if _is_youtube_channel_page(path_segments):
        return YouTubePageKind.channel

    return YouTubePageKind.other


def _extract_channel_ids_with_patterns(content: str, patterns: tuple[re.Pattern[str], ...]) -> set[str]:
    channel_ids: set[str] = set()

    for pattern in patterns:
        channel_ids.update(match.group("channel_id") for match in pattern.finditer(content))

    return channel_ids


def _extract_channel_ids_from_video_page_content(content: str) -> set[str]:
    return _extract_channel_ids_with_patterns(content, _YOUTUBE_VIDEO_PAGE_CHANNEL_PATTERNS)


def _extract_channel_ids_from_channel_page_content(content: str) -> set[str]:
    return _extract_channel_ids_with_patterns(content, _YOUTUBE_CHANNEL_PAGE_CHANNEL_PATTERNS)


def _build_feed_urls_for_channel_ids(channel_ids: set[str], channel_feed_url: str) -> set[AbsoluteUrl]:
    feed_urls: set[AbsoluteUrl] = set()

    for channel_id in channel_ids:
        feed_url = normalize_classic_unknown_url(UnknownUrl(channel_feed_url.format(channel_id=channel_id)))

        if feed_url is not None:
            feed_urls.add(feed_url)

    return feed_urls


async def _load_page_content(url: FeedUrl) -> str | None:
    try:
        response = await lo_domain.load_content_with_proxies(url, headers=_YOUTUBE_DISCOVERY_HEADERS)
        return await lo_domain.decode_content(response)
    except lo_errors.LoadError:
        logger.info("discovering_youtube_cannot_access_channel_page", url=url)
        return None


def _normalize_nested_youtube_url(url: str) -> AbsoluteUrl | None:
    if url.startswith("/"):
        assert _YOUTUBE_ROOT_URL is not None
        return adjust_classic_relative_url(UnknownUrl(url), _YOUTUBE_ROOT_URL)

    return normalize_classic_unknown_url(UnknownUrl(url))


def _extract_youtube_video_id_from_url(url: AbsoluteUrl, *, _depth: int = 0) -> str | None:  # noqa: CCR001
    if _depth > 1:
        return None

    f_url = construct_f_url(url)

    if f_url is None or f_url.host is None or not _is_youtube_host(f_url.host.lower()):
        return None

    path = str(f_url.path)
    path_segments = [segment for segment in f_url.path.segments if segment]

    if f_url.host.lower() == "youtu.be":
        return path_segments[0] if path_segments else None

    if path == "/watch":
        for key in ("v", "vi"):
            value = f_url.query.params.get(key)

            if value:
                return value

    if len(path_segments) >= 2 and path_segments[0] in _YOUTUBE_PATH_PREFIXES:
        return path_segments[1]

    if path in {"/attribution_link", "/oembed"}:
        for key in ("u", "url"):
            nested_url = f_url.query.params.get(key)

            if not nested_url:
                continue

            absolute_nested_url = _normalize_nested_youtube_url(nested_url)

            if absolute_nested_url is None:
                continue

            nested_video_id = _extract_youtube_video_id_from_url(absolute_nested_url, _depth=_depth + 1)

            if nested_video_id is not None:
                return nested_video_id

    return None


def _postprocess_reference(reference: Reference) -> Reference:
    if reference.semantics != ReferenceSemantics.video:
        return reference

    youtube_id = _extract_youtube_video_id_from_url(reference.url)

    if youtube_id is None:
        return reference

    if reference.extra is None:
        extra: dict[str, int | float | str | None] = {}
    else:
        extra = reference.extra.copy()

    extra["youtube_id"] = youtube_id

    return reference.replace(extra=extra)


class Plugin(BasePlugin):
    __slots__ = ("_channel_feed_url",)
    source_name = "YouTube"

    def __init__(self, channel_feed_url: str):
        self._channel_feed_url = channel_feed_url

    async def discover_feed_urls(self, context: fd_entities.Context) -> fd_entities.DiscoverResult:
        assert context.url is not None

        page_kind = _detect_youtube_page_kind(context.url)

        if page_kind not in {YouTubePageKind.video, YouTubePageKind.channel}:
            return context, None

        content = await _load_page_content(context.url)

        if content is None:
            return context, None

        if page_kind == YouTubePageKind.video:
            channel_ids = _extract_channel_ids_from_video_page_content(content)
        else:
            channel_ids = _extract_channel_ids_from_channel_page_content(content)

        if not channel_ids:
            return context, None

        candidate_urls = context.candidate_urls | _build_feed_urls_for_channel_ids(channel_ids, self._channel_feed_url)

        return context.replace(candidate_urls=candidate_urls), None

    def postprocess_entry(self, entry: p_entities.EntryInfo) -> p_entities.EntryInfo:
        return entry.replace(
            body=markdown.markdown(_autolink_bare_urls(entry.body)),  # type: ignore
            references=[_postprocess_reference(reference) for reference in entry.references],
        )


def construct(**kwargs: object) -> Plugin:
    channel_feed_url = kwargs.get("channel_feed_url", DEFAULT_CHANNEL_FEED_URL)

    assert isinstance(channel_feed_url, str)

    return Plugin(channel_feed_url=channel_feed_url)
