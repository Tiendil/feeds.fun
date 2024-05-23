import datetime

import pydantic
import pydantic_settings

from ffun.core.settings import BaseSettings


class Proxy(pydantic.BaseModel):
    name: str
    url: str | None = None


class Settings(BaseSettings):
    loaders_number: int = 5
    minimum_period: datetime.timedelta = datetime.timedelta(hours=1)
    proxies: list[Proxy] = [Proxy(name="default", url=None)]

    proxy_anchors: list[str] = ["https://www.google.com", "https://www.amazon.com"]
    proxy_available_check_period: datetime.timedelta = datetime.timedelta(minutes=5)

    model_config = pydantic_settings.SettingsConfigDict(env_prefix="FFUN_LOADER_")


settings = Settings()
