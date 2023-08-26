import datetime

import pydantic_settings

from ffun.core.settings import BaseSettings


class Settings(BaseSettings):
    retry_after: datetime.timedelta = datetime.timedelta(hours=4)

    model_config = pydantic_settings.SettingsConfigDict(env_prefix="FFUN_LIBRARY_")


settings = Settings()
