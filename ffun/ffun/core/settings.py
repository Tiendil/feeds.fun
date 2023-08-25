import pydantic_settings


class BaseSettings(pydantic_settings.BaseSettings):
    model_config = pydantic_settings.SettingsConfigDict(
        env_nested_delimiter="__",
        # TODO: smart search for .env file
        # or update to pydantic-settings when it will be released
        env_file=("../.env", ".env"),
        extra="allow",
    )
