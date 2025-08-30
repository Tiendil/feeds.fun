import datetime
import functools
import pathlib

import pydantic
import pydantic_settings
import toml

from ffun.core.settings import BaseSettings
from ffun.tags.entities import NormalizerConfig, TagNormalizer

_root = pathlib.Path(__file__).parent


class Settings(BaseSettings):
    # TODO: add to documentation/README
    tag_normalizers_config: pathlib.Path = _root / "fixtures" / "tag_normalizers.toml"

    @pydantic.computed_field  # type: ignore
    @functools.cached_property
    def tag_normalizers(self) -> tuple[TagNormalizer, ...]:
        data = toml.loads(self.tag_normalizers_config.read_text())

        return NormalizerConfig(**data).tag_normalizers

    model_config = pydantic_settings.SettingsConfigDict(env_prefix="FFUN_TAGS_")


settings = Settings()
