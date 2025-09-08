import datetime
import functools
import pathlib

import pydantic
import pydantic_settings
import toml

from ffun.core.settings import BaseSettings
from ffun.librarian.entities import ProcessorsConfig, TagProcessor

_root = pathlib.Path(__file__).parent


class Settings(BaseSettings):
    tag_processors_config: pathlib.Path = _root / "fixtures" / "tag_processors.toml"

    metric_accumulation_interval: datetime.timedelta = datetime.timedelta(minutes=10)

    @pydantic.computed_field  # type: ignore
    @functools.cached_property
    def tag_processors(self) -> tuple[TagProcessor, ...]:
        data = toml.loads(self.tag_processors_config.read_text())

        return ProcessorsConfig(**data).tag_processors

    model_config = pydantic_settings.SettingsConfigDict(env_prefix="FFUN_LIBRARIAN_")


settings = Settings()
