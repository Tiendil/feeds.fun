import datetime

import pydantic
from ffun.core.settings import BaseSettings


class PostgreSQL(pydantic.BaseModel):
    dsn: str = 'postgresql://ffun:ffun@postgresql/ffun'
    pool_min_size: int = 20
    pool_max_size: int|None = None
    pool_timeout: float = 0.1
    pool_num_workers: int = 1


class Settings(BaseSettings):  # type: ignore
    name: str = "Feeds Fun"
    domain: str = "localhost"

    enable_api: bool = False
    enable_supertokens: bool = False

    postgresql: PostgreSQL = PostgreSQL()

    class Config:
        env_prefix = "FFUN_"


settings = Settings()
