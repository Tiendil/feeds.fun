import datetime

import pydantic

from ffun.core.settings import BaseSettings


class PostgreSQL(pydantic.BaseModel):
    dsn: str = "postgresql://ffun:ffun@postgresql/ffun"
    pool_min_size: int = 20
    pool_max_size: int | None = None
    pool_timeout: float = 1
    pool_num_workers: int = 1
    pool_max_lifetime: int = 9 * 60
    pool_check_period: int = 60


class Sentry(pydantic.BaseModel):
    dsn: str = ""
    sample_rate: float = 1.0
    traces_sample_rate: float = 1.0


class Settings(BaseSettings):
    app_name: str = "Feeds Fun"
    app_domain: str = "localhost"
    app_port: int = 5173

    environment: str = "local"

    api_port: int = 5174

    enable_api: bool = False
    enable_supertokens: bool = False
    enable_sentry: bool = False

    postgresql: PostgreSQL = PostgreSQL()
    sentry: Sentry = Sentry()

    class Config:
        env_prefix = "FFUN_"


settings = Settings()
