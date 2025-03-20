import pydantic_settings

from ffun.core.settings import BaseSettings
from ffun.domain.entities import CollectionSlug


class Settings(BaseSettings):
    max_returned_entries: int = 10000
    max_feeds_suggestions_for_site: int = 100
    max_entries_suggestions_for_site: int = 3
    max_entries_details_requests: int = 100

    # TODO: do we actually need a default slug here?
    #       check the final implementation of public collections frontend
    #       remove from everywhere if not required
    default_public_collection_slug: CollectionSlug | None = None

    model_config = pydantic_settings.SettingsConfigDict(env_prefix="FFUN_API_")


settings = Settings()
