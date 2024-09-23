import pathlib

import pydantic_settings

from ffun.core.settings import BaseSettings

_root = pathlib.Path(__file__).parent


class Settings(BaseSettings):
    collection_configs: pathlib.Path | None = None

    model_config = pydantic_settings.SettingsConfigDict(env_prefix="FFUN_FEEDS_COLLECTIONS_")


settings = Settings()
