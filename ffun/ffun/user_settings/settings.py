import pydantic_settings

from ffun.core import logging
from ffun.core.settings import BaseSettings

logger = logging.get_module_logger()


# this is key for development!
# MUST be changed in production
_default_secret_key = "JHBC3P8q9nhDNStpfljJ7eO09XNztJ3xWKI5l6rvL-Q="  # noqa: S105


class Settings(BaseSettings):
    secret_key: str = _default_secret_key

    model_config = pydantic_settings.SettingsConfigDict(env_prefix="FFUN_USER_SETTINGS_")


settings = Settings()


if settings.secret_key == _default_secret_key:
    logger.error("user_settings_secret_key_not_changed")
