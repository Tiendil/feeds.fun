import datetime

import pydantic
from ffun.core.settings import BaseSettings


class PostgreSQL(pydantic.BaseModel):
    dsn: str = 'postgresql://ffun:ffun@postgresql/ffun'
    pool_min_size: int = 20
    pool_max_size: int|None = None
    pool_timeout: float = 1
    pool_num_workers: int = 1
    pool_max_lifetime: int = 9 * 60


class Settings(BaseSettings):  # type: ignore
    app_name: str = "Feeds Fun"
    app_domain: str = "localhost"
    app_port: int = 5173

    # TODO: fix duplicated config?
    api_port: int = 5174

    enable_api: bool = False
    enable_supertokens: bool = False

    postgresql: PostgreSQL = PostgreSQL()

    class Config:
        env_prefix = "FFUN_"


settings = Settings()
