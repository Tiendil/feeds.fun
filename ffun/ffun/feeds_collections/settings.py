import pathlib
from typing import Any

import pydantic
import pydantic_settings

from ffun.core.settings import BaseSettings

_root = pathlib.Path(__file__).parent


class Settings(BaseSettings):
    collection_configs: pathlib.Path | None = None

    model_config = pydantic_settings.SettingsConfigDict(env_prefix="FFUN_FEEDS_COLLECTIONS_")

    @pydantic.field_validator("collection_configs", mode="before")
    @classmethod
    def detect_disabled_collection_configs(cls, v: Any) -> Any:
        if v == "":
            return None

        return v


settings = Settings()
