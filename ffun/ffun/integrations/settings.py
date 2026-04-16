from functools import cached_property

import pydantic
import pydantic_settings

from ffun.core.plugins import build_plugin
from ffun.core.settings import BaseSettings
from ffun.domain.entities import SourceUid
from ffun.domain.urls import SourceUidField
from ffun.integrations.plugin import Plugin


class Integration(BaseSettings):
    source: SourceUidField
    plugin: str
    extras: dict[str, str] = pydantic.Field(default_factory=dict)

    @cached_property
    def plugin_instance(self) -> Plugin:
        return build_plugin(Plugin, self.plugin, self.extras)


class Settings(BaseSettings):

    integrations: list[Integration] = pydantic.Field(
        default_factory=lambda: [
            Integration(
                source="reddit.com",
                plugin="ffun.integrations.plugins.reddit:construct",
                extras={},
            ),
            Integration(
                source="github.com",
                plugin="ffun.integrations.plugins.github:construct",
                extras={},
            ),
            Integration(
                source="youtube.com",
                plugin="ffun.integrations.plugins.youtube:construct",
                extras={},
            ),
            Integration(
                source="news.ycombinator.com",
                plugin="ffun.integrations.plugins.hacker_news:construct",
                extras={},
            ),
        ]
    )

    model_config = pydantic_settings.SettingsConfigDict(env_prefix="FFUN_INTEGRATIONS_")

    def get_integration_by_source(self, source: SourceUid) -> Integration | None:
        for integration in self.integrations:
            if integration.source == source:
                return integration

        return None


settings = Settings()
