import enum

import pydantic
import pydantic_settings

from ffun.core.settings import BaseSettings


class AuthMode(str, enum.Enum):
    single_user = "single_user"
    supertokens = "supertokens"


class SingleUser(pydantic.BaseModel):
    external_id: str = "user-for-development"


class Supertokens(pydantic.BaseModel):
    connection_uri: str = "http://supertokens:3567"
    api_key: str = "nn4PGU5rJ3tEe9if4zEJ"  # this is a fake key for tests
    cookie_secure: bool = False

    api_base_path: str = "/supertokens"
    website_base_path: str = "/auth"


class Settings(BaseSettings):
    mode: AuthMode = AuthMode.single_user
    single_user: SingleUser = SingleUser()
    supertokens: Supertokens = Supertokens()

    model_config = pydantic_settings.SettingsConfigDict(env_prefix="FFUN_AUTH_")


settings = Settings()
