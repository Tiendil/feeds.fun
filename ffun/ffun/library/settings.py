import datetime

import pydantic

from ffun.core.settings import BaseSettings


class Settings(BaseSettings):
    retry_after: datetime.timedelta = datetime.timedelta(hours=4)

    class Config:
        env_prefix = "FFUN_LIBRARY_"


settings = Settings()
