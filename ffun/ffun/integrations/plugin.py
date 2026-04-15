from ffun.feeds_discoverer import entities as fd_entities
from ffun.parsers import entities as p_entities


class Plugin:
    __slots__ = ()

    async def discover_feed_urls(self, context: fd_entities.Context) -> fd_entities.DiscoverResult:
        raise NotImplementedError("discover_feed_urls must be implemented by the plugin")

    def postprocess_entry(self, entry: p_entities.EntryInfo) -> p_entities.EntryInfo:
        return entry
