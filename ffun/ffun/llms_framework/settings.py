import datetime
import functools
import pathlib

import pydantic
import pydantic_settings
import toml

from ffun.core import logging
from ffun.core.settings import BaseSettings
from ffun.llms_framework.entities import ModelInfo

logger = logging.get_module_logger()


_root = pathlib.Path(__file__).parent


class ModelInfos(pydantic.BaseModel):
    models: list[ModelInfo]


class Settings(BaseSettings):
    # TODO: add to documentation/README
    models_descriptions: pathlib.Path = _root / "fixtures" / "models.toml"

    key_quota_timeout: datetime.timedelta = datetime.timedelta(hours=1)
    key_broken_timeout: datetime.timedelta = datetime.timedelta(hours=1)

    @pydantic.computed_field  # type: ignore
    @functools.cached_property
    def models(self) -> list[ModelInfo]:
        data = toml.loads(self.models_descriptions.read_text())

        return ModelInfos(**data).models

    model_config = pydantic_settings.SettingsConfigDict(env_prefix="FFUN_LLMS_FRAMEWORK_")


settings = Settings()
