import datetime

import pydantic_settings

from ffun.core.settings import BaseSettings


class Settings(BaseSettings):
    tags_cache_reset_interval: datetime.timedelta = datetime.timedelta(minutes=60)

    model_config = pydantic_settings.SettingsConfigDict(env_prefix="FFUN_ONTOLOGY_")


settings = Settings()
