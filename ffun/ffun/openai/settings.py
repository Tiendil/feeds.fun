import datetime

import pydantic_settings

from ffun.core.settings import BaseSettings


class Settings(BaseSettings):
    key_quota_timeout: datetime.timedelta = datetime.timedelta(hours=1)
    key_broken_timeout: datetime.timedelta = datetime.timedelta(hours=1)

    model_config = pydantic_settings.SettingsConfigDict(env_prefix="FFUN_OPENAI_")


settings = Settings()
