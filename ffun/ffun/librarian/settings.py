import pydantic


class OpenAI(pydantic.BaseModel):  # type: ignore
    enabled: bool = False
    api_key: str = 'fake-api-key'


class Settings(pydantic.BaseSettings):  # type: ignore
    openai: OpenAI = OpenAI()

    class Config:
        env_nested_delimiter: str = "__"
        env_file: str = ".env"
        env_prefix = "FFUN_LIBRARIAN_"
        extra: str = "allow"


settings = Settings()
