import pydantic
import pydantic_settings

from ffun.core.settings import BaseSettings


class PostgreSQL(pydantic.BaseModel):
    host: str = "postgresql"
    port: int = 5432
    user: str = "ffun"
    password: str = "ffun"
    database: str = "ffun"

    pool_min_size: int = 20
    pool_max_size: int | None = None
    pool_timeout: float = 1.0
    pool_num_workers: int = 1
    pool_max_lifetime: int = 9 * 60
    pool_check_period: int = 60

    @property
    def dsn(self) -> str:
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"

    @property
    def dsn_yoyo(self) -> str:
        return f"postgresql+psycopg://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"


class Sentry(pydantic.BaseModel):
    dsn: str = ""
    sample_rate: float = 1.0
    traces_sample_rate: float = 1.0


_development_origins = ("*",)


class Settings(BaseSettings):
    app_name: str = "Feeds Fun"
    app_domain: str = "localhost"
    app_port: int = 5173

    environment: str = "local"

    api_port: int = 5174

    enable_api: bool = False
    enable_sentry: bool = False

    postgresql: PostgreSQL = PostgreSQL()
    sentry: Sentry = Sentry()

    origins: tuple[str, ...] = _development_origins

    @pydantic.model_validator(mode="after")
    def origin_must_be_redefined_in_prod(self) -> "Settings":
        if self.environment == "prod" and self.origins == _development_origins:
            raise ValueError("Origins must be redefined in prod")

        return self

    model_config = pydantic_settings.SettingsConfigDict(env_prefix="FFUN_")


settings = Settings()
