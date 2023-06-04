import pydantic
from ffun.core.settings import BaseSettings


class BaseProcessor(pydantic.BaseModel):  # type: ignore
    id: int
    name: str
    enabled: bool = False
    workers: int = 1


class DomainProcessor(BaseProcessor):  # type: ignore
    pass


class NativeTagsProcessor(BaseProcessor):  # type: ignore
    pass


class OpenAIChat35Processor(BaseProcessor):  # type: ignore
    api_key: str = 'fake-api-key'


class Settings(BaseSettings):  # type: ignore
    domain_processor: DomainProcessor = DomainProcessor(id=1, name='domain', enabled=True)
    native_tags_processor: NativeTagsProcessor = NativeTagsProcessor(id=2, enabled=True)
    openai_chat_35_processor: OpenAIChat35Processor = OpenAIChat35Processor(id=3)

    class Config:
        env_prefix = "FFUN_LIBRARIAN_"


settings = Settings()
