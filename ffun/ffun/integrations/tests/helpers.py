from ffun.domain.entities import SourceUid
from ffun.integrations.plugins import fake as fake_plugin


class FakeIntegration:
    def __init__(self, source: str, urls: list[str]):
        self.source = SourceUid(source)
        self.plugin_instance = fake_plugin.construct(urls=urls)
