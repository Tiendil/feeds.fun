import pydantic_settings

from ffun.core.settings import BaseSettings


class Settings(BaseSettings):
    dispatch_batch_size: int = 1000
    dispatch_concurrency: int = 20

    model_config = pydantic_settings.SettingsConfigDict(env_prefix="FFUN_DISPATCHER_")


settings = Settings()
