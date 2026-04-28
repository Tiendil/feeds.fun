from ffun.feeds_discoverer import entities as fd_entities
from ffun.integrations.plugin import Plugin
from ffun.parsers import entities as p_entities


class TestPlugin:
    def test_supports_discovery__returns_false_for_base_plugin(self) -> None:
        plugin = Plugin()

        assert not plugin.supports_discovery

    def test_supports_discovery__returns_true_if_discover_feed_urls_redefined(self) -> None:
        class DerivedPlugin(Plugin):
            async def discover_feed_urls(self, context: fd_entities.Context) -> fd_entities.DiscoverResult:
                return context, None

        plugin = DerivedPlugin()

        assert plugin.supports_discovery

    def test_supports_entry_postprocessing__returns_false_for_base_plugin(self) -> None:
        plugin = Plugin()

        assert not plugin.supports_entry_postprocessing

    def test_supports_entry_postprocessing__returns_true_if_postprocess_entry_redefined(self) -> None:
        class DerivedPlugin(Plugin):
            def postprocess_entry(self, entry: p_entities.EntryInfo) -> p_entities.EntryInfo:
                return entry

        plugin = DerivedPlugin()

        assert plugin.supports_entry_postprocessing
