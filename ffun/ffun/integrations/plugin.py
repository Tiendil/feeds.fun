from ffun.feeds_discoverer import entities as fd_entities
from ffun.parsers import entities as p_entities


class Plugin:
    __slots__ = ()

    @property
    def supports_discovery(self) -> bool:
        return type(self).discover_feed_urls is not Plugin.discover_feed_urls

    @property
    def supports_entry_postprocessing(self) -> bool:
        return type(self).postprocess_entry is not Plugin.postprocess_entry

    async def discover_feed_urls(self, context: fd_entities.Context) -> fd_entities.DiscoverResult:
        return context, None

    def postprocess_entry(self, entry: p_entities.EntryInfo) -> p_entities.EntryInfo:
        return entry
