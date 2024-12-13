import pydantic_settings

from ffun.core.settings import BaseSettings


class Settings(BaseSettings):
    max_returned_entries: int = 10000
    max_feeds_suggestions_for_site: int = 100
    max_entries_suggestions_for_site: int = 3

    model_config = pydantic_settings.SettingsConfigDict(env_prefix="FFUN_API_")


settings = Settings()
