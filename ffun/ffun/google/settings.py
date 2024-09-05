import pathlib

import pydantic_settings

from ffun.core.settings import BaseSettings

_root = pathlib.Path(__file__).parent


class Settings(BaseSettings):

    gemini_api_entry_point: str = "https://generativelanguage.googleapis.com/v1beta"
    gemini_api_timeout: float = 20.0

    model_config = pydantic_settings.SettingsConfigDict(env_prefix="FFUN_GOOGLE_")


settings = Settings()
