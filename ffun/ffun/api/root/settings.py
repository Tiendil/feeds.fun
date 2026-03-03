import pydantic
import pydantic_settings

from ffun.core.settings import BaseSettings

_default_sitemaps = ["/sitemaps/pages.xml", "/blog/sitemap.xml"]

_default_robots_extra_disallowed_paths = ["/blog/en/tags/"]


class Settings(BaseSettings):
    sitemaps: list[str] = pydantic.Field(default_factory=lambda: list(_default_sitemaps))
    robots_extra_disallowed_paths: list[str] = pydantic.Field(
        default_factory=lambda: list(_default_robots_extra_disallowed_paths)
    )

    model_config = pydantic_settings.SettingsConfigDict(env_prefix="FFUN_API_ROOT_")


settings = Settings()
