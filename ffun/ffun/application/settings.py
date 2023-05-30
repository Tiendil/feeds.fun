import datetime

from ffun.core.settings import BaseSettings


class Settings(BaseSettings):  # type: ignore
    name: str = "Feeds Fun"
    domain: str = "localhost"

    enable_api: bool = False
    enable_supertokens: bool = False

    class Config:
        env_prefix = "FFUN_"


settings = Settings()
