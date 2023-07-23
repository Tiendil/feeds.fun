import datetime

import pydantic

from ffun.core.settings import BaseSettings


class Proxy(pydantic.BaseModel):
    name: str
    url: str | None = None


class Settings(BaseSettings):
    loaders_number: int = 5
    minimum_period: datetime.timedelta = datetime.timedelta(hours=1)
    proxies: list[Proxy] = [Proxy(name="default", url=None)]

    class Config:
        env_prefix = "FFUN_LOADER_"


settings = Settings()
