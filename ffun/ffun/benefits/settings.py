import functools
import pathlib

import pydantic
import pydantic_settings
import toml

from ffun.benefits.entities import BenefitPackageTemplate
from ffun.core.settings import BaseSettings


class PackageTemplatesConfig(pydantic.BaseModel):
    # Keep package ids stable: do not reuse an id for an unrelated product or
    # remove one while a current subscription can reference it.
    package_templates: tuple[BenefitPackageTemplate, ...]

    @pydantic.model_validator(mode="after")
    def package_template_ids_must_be_unique(self) -> "PackageTemplatesConfig":
        template_ids = [template.id for template in self.package_templates]

        if len(template_ids) != len(set(template_ids)):
            raise ValueError("Benefit package template ids must be unique")

        return self


class Settings(BaseSettings):
    package_templates_config: pathlib.Path | None = None

    @pydantic.computed_field  # type: ignore
    @functools.cached_property
    def package_templates(self) -> tuple[BenefitPackageTemplate, ...]:
        if self.package_templates_config is None:
            return ()

        data: dict[str, object] = toml.loads(self.package_templates_config.read_text())

        return PackageTemplatesConfig.model_validate(data).package_templates

    model_config = pydantic_settings.SettingsConfigDict(env_prefix="FFUN_BENEFITS_")


settings = Settings()
