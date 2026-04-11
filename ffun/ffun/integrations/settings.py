
import pydantic
import pydantic_settings

from ffun.integrations.plugin import Plugin
from ffun.core import utils
from ffun.core.settings import BaseSettings
from ffun.domain.entities import SourceUid
from ffun.domain.urls import SourceUidField


class Integration(BaseSettings):
    source: SourceUidField
    plugin: Plugin
    extras: dict[str, str] = pydantic.Field(default_factory=dict)

    # TODO: make build_plugin a mixing or a specifalized field type (parametrized by the type of plugin)
    @pydantic.model_validator(mode="before")
    @classmethod
    def build_plugin(cls, data: object) -> object:
        if not isinstance(data, dict):
            return data

        v = data.get("plugin")

        if not isinstance(v, str):
            raise ValueError("plugin must be defined as a string module.path:callable_constructor")

        extras = data.get("extras", {}) or {}  # type: ignore

        try:
            constructor = utils.import_from_string(v)
        except Exception as e:
            raise ValueError(f"Cannot import '{v}': {e}") from e

        try:
            data["plugin"] = constructor(**extras)  # type: ignore
        except Exception as e:
            raise ValueError(f"Cannot construct plugin from '{v}': {e}") from e

        return data


class Settings(BaseSettings):

    integrations: list[Integration] = pydantic.Field(
        default_factory=lambda: [
            Integration(
                source="reddit.com",
                plugin="ffun.integrations.plugins.reddit:construct",  # type: ignore
            )
        ]
    )

    model_config = pydantic_settings.SettingsConfigDict(env_prefix="FFUN_INTEGRATIONS_")

    def get_integration_by_source(self, source: SourceUid) -> Integration | None:
        for integration in self.integrations:
            if integration.source == source:
                return integration

        return None


settings = Settings()
