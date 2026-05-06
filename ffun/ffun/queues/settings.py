import datetime

import pydantic_settings

from ffun.core.settings import BaseSettings


class Settings(BaseSettings):
    freezing_delay: datetime.timedelta = datetime.timedelta(hours=1)

    model_config = pydantic_settings.SettingsConfigDict(env_prefix="FFUN_QUEUES_")


settings = Settings()
