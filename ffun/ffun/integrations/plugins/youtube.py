import re

import markdown

from ffun.feeds_discoverer import entities as fd_entities
from ffun.integrations.plugin import Plugin as BasePlugin
from ffun.parsers import entities as p_entities

_BARE_URL_RE = re.compile(r'(?<!\()(?<!<)(?<!")(?P<url>https?://[^\s<]+)')


def _autolink_bare_urls(text: str) -> str:
    def _replace(match: re.Match[str]) -> str:
        url = match.group("url")
        stripped_url = url.rstrip(".,!?;:")

        if stripped_url == "":
            return url

        suffix = url[len(stripped_url) :]
        return f"<{stripped_url}>{suffix}"

    return _BARE_URL_RE.sub(_replace, text)


class Plugin(BasePlugin):
    __slots__ = ()

    async def discover_feed_urls(self, context: fd_entities.Context) -> fd_entities.DiscoverResult:
        return context, None

    def postprocess_entry(self, entry: p_entities.EntryInfo) -> p_entities.EntryInfo:
        return entry.model_copy(update={"body": markdown.markdown(_autolink_bare_urls(entry.body))})


def construct() -> Plugin:
    return Plugin()
