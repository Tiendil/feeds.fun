import re
from urllib.parse import parse_qs, unquote, urlsplit

import markdown

from ffun.domain.entities import AbsoluteUrl
from ffun.feeds_discoverer import entities as fd_entities
from ffun.integrations.plugin import Plugin as BasePlugin
from ffun.library.entities import Reference, ReferenceSemantics
from ffun.parsers import entities as p_entities

_BARE_URL_RE = re.compile(r'(?<!\()(?<!<)(?<!")(?P<url>https?://[^\s<]+)')
_YOUTUBE_PATH_PREFIXES = {"embed", "e", "live", "shorts", "v"}


def _autolink_bare_urls(text: str) -> str:
    def _replace(match: re.Match[str]) -> str:
        url = match.group("url")
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


def _extract_youtube_video_id_from_url(url: AbsoluteUrl, *, _depth: int = 0) -> str | None:
    if _depth > 1:
        return None

    parsed_url = urlsplit(url)
    hostname = parsed_url.hostname

    if hostname is None or not _is_youtube_host(hostname.lower()):
        return None

    path_segments = [segment for segment in parsed_url.path.split("/") if segment]

    if hostname.lower() == "youtu.be":
        return path_segments[0] if path_segments else None

    if parsed_url.path == "/watch":
        query = parse_qs(parsed_url.query)
        for key in ("v", "vi"):
            values = query.get(key)

            if values:
                return values[0]

    if len(path_segments) >= 2 and path_segments[0] in _YOUTUBE_PATH_PREFIXES:
        return path_segments[1]

    if parsed_url.path in {"/attribution_link", "/oembed"}:
        query = parse_qs(parsed_url.query)

        for key in ("u", "url"):
            values = query.get(key)

            if not values:
                continue

            nested_url = unquote(values[0])

            if nested_url.startswith("/"):
                nested_url = f"https://www.youtube.com{nested_url}"

            nested_video_id = _extract_youtube_video_id_from_url(AbsoluteUrl(nested_url), _depth=_depth + 1)

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
    __slots__ = ()

    async def discover_feed_urls(self, context: fd_entities.Context) -> fd_entities.DiscoverResult:
        return context, None

    def postprocess_entry(self, entry: p_entities.EntryInfo) -> p_entities.EntryInfo:
        return entry.model_copy(
            update={
                "body": markdown.markdown(_autolink_bare_urls(entry.body)),
                "references": [_postprocess_reference(reference) for reference in entry.references],
            }
        )


def construct() -> Plugin:
    return Plugin()
