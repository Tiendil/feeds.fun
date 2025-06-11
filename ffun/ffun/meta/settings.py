import datetime

import pydantic_settings

from ffun.core.settings import BaseSettings


class Settings(BaseSettings):
    delay_before_removing_orphaned_feeds: datetime.timedelta = datetime.timedelta(days=1)

    model_config = pydantic_settings.SettingsConfigDict(env_prefix="FFUN_META_")


settings = Settings()
