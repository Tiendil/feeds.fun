import pydantic
import pydantic_settings

from ffun.benefits.entities import BenefitPackage
from ffun.core.settings import BaseSettings


class Settings(BaseSettings):
    # Until benefits become persisted entities, this configuration is append-only:
    # never remove or change an existing package; introduce a new id instead.
    packages: tuple[BenefitPackage, ...] = ()

    @pydantic.model_validator(mode="after")
    def package_ids_must_be_unique(self) -> "Settings":
        package_ids = [package.id for package in self.packages]

        if len(package_ids) != len(set(package_ids)):
            raise ValueError("Benefit package ids must be unique")

        return self

    model_config = pydantic_settings.SettingsConfigDict(env_prefix="FFUN_BENEFITS_")


settings = Settings()
