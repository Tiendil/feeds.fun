import datetime

import pydantic


class Settings(pydantic.BaseSettings):  # type: ignore
    loaders_number: int = 5
    minimum_period: datetime.timedelta = datetime.timedelta(minutes=10)

    class Config:
        env_nested_delimiter: str = "__"
        env_file: str = ".env"
        env_prefix = "FFUN_LOADER_"
        extra: str = "allow"


settings = Settings()
