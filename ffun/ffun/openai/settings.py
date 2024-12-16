import pathlib

import pydantic_settings

from ffun.core.settings import BaseSettings

_root = pathlib.Path(__file__).parent


class Settings(BaseSettings):

    api_entry_point: str | None = None
    api_timeout: float = 20.0

    model_config = pydantic_settings.SettingsConfigDict(env_prefix="FFUN_OPENAI_")


settings = Settings()
