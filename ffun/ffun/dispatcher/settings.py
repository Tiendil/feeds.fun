import pydantic_settings

from ffun.core.settings import BaseSettings


class Settings(BaseSettings):
    dispatch_chunk: int = 1000

    model_config = pydantic_settings.SettingsConfigDict(env_prefix="FFUN_DISPATCHER_")


settings = Settings()
