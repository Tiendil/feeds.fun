import pydantic_settings
import datetime

from ffun.core.settings import BaseSettings


class Settings(BaseSettings):
    max_entries_per_feed: int = 10000
    max_entry_age: datetime.timedelta = datetime.timedelta(days=30)

    model_config = pydantic_settings.SettingsConfigDict(env_prefix="FFUN_LIBRARY_")


settings = Settings()
