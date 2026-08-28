import pydantic
import pydantic_settings

from ffun.benefits.entities import BenefitPackageTemplate
from ffun.core.settings import BaseSettings


class Settings(BaseSettings):
    # Keep package ids stable: do not reuse an id for an unrelated product or
    # remove one while a current subscription can reference it.
    package_templates: tuple[BenefitPackageTemplate, ...] = ()

    @pydantic.model_validator(mode="after")
    def package_template_ids_must_be_unique(self) -> "Settings":
        template_ids = [template.id for template in self.package_templates]

        if len(template_ids) != len(set(template_ids)):
            raise ValueError("Benefit package template ids must be unique")

        return self

    model_config = pydantic_settings.SettingsConfigDict(env_prefix="FFUN_BENEFITS_")


settings = Settings()
