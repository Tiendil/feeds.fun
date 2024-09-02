import datetime
import toml
import functools
import pathlib
import pydantic
import pydantic_settings

from ffun.core import logging
from ffun.core.settings import BaseSettings

from ffun.llms_framework.entities import ModelInfo

logger = logging.get_module_logger()


_root = pathlib.Path(__file__).parent


class ModelInfos(pydantic.BaseModel):
    models = list[ModelInfo]


class Settings(BaseSettings):
    # TODO: add to documentation/README
    models_description: pathlib.Path = _root / "fixtures" / "models.toml"

    @pydantic.computed_field
    @functools.cached_property
    def models(self) -> ModelInfo:
        data = toml.loads(self.models_description.read_text())

        return ModelInfos(**data).models


settings = Settings()
