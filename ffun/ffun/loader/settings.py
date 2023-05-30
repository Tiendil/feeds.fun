import datetime

from ffun.core.settings import BaseSettings


class Settings(BaseSettings):  # type: ignore
    loaders_number: int = 5
    minimum_period: datetime.timedelta = datetime.timedelta(minutes=10)

    class Config:
        env_prefix = "FFUN_LOADER_"


settings = Settings()
