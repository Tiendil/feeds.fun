import datetime

import pydantic


class Supertokens(pydantic.BaseModel):  # type: ignore
    connection_uri: str = "http://localhost:3567"
    api_key: str = "fake-api-key"
    mode = 'asgi'


class Settings(pydantic.BaseSettings):  # type: ignore
    supertokens: Supertokens = Supertokens()

    class Config:
        env_nested_delimiter: str = "__"
        env_file: str = ".env"
        env_prefix = "FFUN_SUPERTOKENS_"
        extra: str = "allow"


settings = Settings()
