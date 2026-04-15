from ffun.domain.urls import str_to_absolute_url
from ffun.feeds_discoverer import entities as fd_entities
from ffun.integrations.plugin import Plugin as BasePlugin
from ffun.parsers import entities as p_entities


class Plugin(BasePlugin):
    __slots__ = ("_urls",)

    def __init__(self, urls: list[str]):
        self._urls = {str_to_absolute_url(url) for url in urls}

    async def discover_feed_urls(self, context: fd_entities.Context) -> fd_entities.DiscoverResult:
        return context.replace(candidate_urls=context.candidate_urls | self._urls), None

    def postprocess_entry(self, entry: p_entities.EntryInfo) -> p_entities.EntryInfo:
        external_tags = set(entry.external_tags)
        external_tags.add("fake-plugin")
        update: dict[str, object] = {"external_tags": external_tags}
        return entry.model_copy(update=update)


def construct(urls: list[str]) -> Plugin:
    return Plugin(urls=urls)
