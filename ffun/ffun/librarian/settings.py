import pydantic
from ffun.core.settings import BaseSettings


class OpenAI(pydantic.BaseModel):  # type: ignore
    enabled: bool = False
    api_key: str = 'fake-api-key'


class Settings(BaseSettings):  # type: ignore
    openai: OpenAI = OpenAI()

    class Config:
        env_prefix = "FFUN_LIBRARIAN_"


settings = Settings()
