import datetime

import pydantic
import pydantic_settings

from ffun.core import logging
from ffun.core.settings import BaseSettings

logger = logging.get_module_logger()


class Settings(BaseSettings):
    key_quota_timeout: datetime.timedelta = datetime.timedelta(hours=1)
    key_broken_timeout: datetime.timedelta = datetime.timedelta(hours=1)

    model_config = pydantic_settings.SettingsConfigDict(env_prefix="FFUN_OPENAI_")

    collections_api_key: str | None = None
    general_api_key: str | None = None

    @pydantic.model_validator(mode="after")
    def collections_api_key_warning(self) -> "Settings":
        if self.collections_api_key is None:
            logger.warning("collections_api_key_is_not_set", comment="Collection feeds will be treated as general")

    @pydantic.model_validator(mode="after")
    def general_api_key_must_be_none_in_prod(self) -> "Settings":
        # TODO: this component should not depend on the environment
        #       move environment settings to the domain component
        from ffun.application.settings import settings as app_settings

        if app_settings.environment == "prod" and self.general_api_key is not None:
            raise ValueError("General API key must be None in prod")

        return self


settings = Settings()
