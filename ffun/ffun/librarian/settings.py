import pathlib
import functools
import toml
from typing import Literal

import pydantic
import pydantic_settings

from ffun.core.settings import BaseSettings
from ffun.librarian.entities import ProcessorsConfig, TagProcessor


_root = pathlib.Path(__file__).parent


class Settings(BaseSettings):
    # TODO: add to documentation/README
    tag_processors_config: pathlib.Path = _root / "fixtures" / "tag_processors.toml"

    # TODO: tests
    @pydantic.computed_field
    @functools.cached_property
    def tag_processors(self) -> tuple[TagProcessor, ...]:
        data = toml.loads(self.models_description.read_text())

        return ProcessorsConfig(**data).processors

    model_config = pydantic_settings.SettingsConfigDict(env_prefix="FFUN_LIBRARIAN_")


settings = Settings()
