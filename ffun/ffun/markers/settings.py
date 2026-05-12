import pydantic_settings

from ffun.core.settings import BaseSettings
from ffun.markers.entities import Marker


class Settings(BaseSettings):
    log_business_events_for: list[Marker] = [Marker.read]

    model_config = pydantic_settings.SettingsConfigDict(env_prefix="FFUN_MARKERS_")


settings = Settings()
