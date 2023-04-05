import pydantic


class OpenAI(pydantic.BaseModel):  # type: ignore
    api_key: str
    model: str = 'gpt-3.5-turbo'


class Settings(pydantic.BaseSettings):  # type: ignore
    openai: OpenAI

    class Config:
        env_nested_delimiter: str = "__"
        env_file: str = ".env"
        env_prefix = "FFUN_LIBRARIAN_"
        extra: str = "allow"


settings = Settings()
