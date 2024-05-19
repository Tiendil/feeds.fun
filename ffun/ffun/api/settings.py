import pydantic_settings

from ffun.core.settings import BaseSettings


class Settings(BaseSettings):
    max_returned_entries: int = 10000

    model_config = pydantic_settings.SettingsConfigDict(env_prefix="FFUN_API_")


settings = Settings()
