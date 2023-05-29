import datetime
import enum
import uuid

import pydantic


class AuthMode(str, enum.Enum):
    single_user = 'single_user'
    supertokens = 'supertokens'


class SingleUser(pydantic.BaseModel):  # type: ignore
    external_id: str = "user-for-development"


class Supertokens(pydantic.BaseModel):  # type: ignore
    connection_uri: str = "http://supertokens:3567"
    api_key: str = "nn4PGU5rJ3tEe9if4zEJ"  # this is a fake key for tests
    mode = 'asgi'


class Settings(pydantic.BaseSettings):  # type: ignore
    mode: AuthMode = AuthMode.single_user
    single_user: SingleUser = SingleUser()
    supertokens: Supertokens = Supertokens()

    class Config:
        env_nested_delimiter: str = "__"
        env_file: str = ".env"
        env_prefix = "FFUN_AUTH_"
        extra: str = "allow"


settings = Settings()
