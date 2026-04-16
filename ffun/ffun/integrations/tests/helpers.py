from ffun.domain.entities import SourceUid
from ffun.integrations.plugins import fake as fake_plugin


class FakeIntegration:
    def __init__(self, sources: str | list[str], urls: list[str]):
        raw_sources = [sources] if isinstance(sources, str) else sources
        self.sources = [SourceUid(source) for source in raw_sources]
        self.plugin_instance = fake_plugin.construct(urls=urls)
