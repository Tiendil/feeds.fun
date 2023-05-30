import datetime

import pydantic


class Settings(pydantic.BaseSettings):  # type: ignore
    name: str = "Feeds Fun"
    domain: str = "localhost"

    enable_api: bool = False
    enable_supertokens: bool = False

    class Config:
        env_nested_delimiter: str = "__"
        env_file: str = ".env"
        env_prefix = "FFUN_"
        extra: str = "allow"


settings = Settings()
