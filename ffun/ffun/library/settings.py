import datetime

import pydantic


class Settings(pydantic.BaseSettings):  # type: ignore
    retry_after: datetime.timedelta = datetime.timedelta(hours=4)

    class Config:
        env_nested_delimiter: str = "__"
        env_file: str = ".env"
        env_prefix = "FFUN_LIBRARY_"
        extra: str = "allow"


settings = Settings()
