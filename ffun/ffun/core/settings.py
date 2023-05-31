import pydantic


class BaseSettings(pydantic.BaseSettings):  # type: ignore

    class Config:
        env_nested_delimiter = "__"
        # TODO: smart search for .env file
        # or update to pydantic-settings when it will be released
        env_file = ("../.env", ".env")
        extra = "allow"
