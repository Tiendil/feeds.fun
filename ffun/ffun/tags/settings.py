import datetime
import functools
import pathlib

import pydantic
import pydantic_settings
import toml

from ffun.core.settings import BaseSettings
from ffun.tags.entities import NormalizersConfig, TagNormalizer

_root = pathlib.Path(__file__).parent


class Settings(BaseSettings):
    tag_normalizers_config: pathlib.Path = _root / "fixtures" / "tag_normalizers.toml"

    metric_accumulation_interval: datetime.timedelta = datetime.timedelta(minutes=10)

    @pydantic.computed_field  # type: ignore
    @functools.cached_property
    def tag_normalizers(self) -> tuple[TagNormalizer, ...]:
        data = toml.loads(self.tag_normalizers_config.read_text())

        return NormalizersConfig(**data).tag_normalizer

    model_config = pydantic_settings.SettingsConfigDict(env_prefix="FFUN_TAGS_")


settings = Settings()
