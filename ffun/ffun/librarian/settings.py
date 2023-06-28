import pydantic
from ffun.core.settings import BaseSettings


class BaseProcessor(pydantic.BaseModel):  # type: ignore
    enabled: bool = False
    workers: int = 1


class DomainProcessor(BaseProcessor):  # type: ignore
    pass


class NativeTagsProcessor(BaseProcessor):  # type: ignore
    pass


class OpenAIChat35Processor(BaseProcessor):  # type: ignore
    api_key: str = 'fake-api-key'


class OpenAIChat35ProcessorFunctions(BaseProcessor):  # type: ignore
    api_key: str = 'fake-api-key'


class Settings(BaseSettings):  # type: ignore
    domain_processor: DomainProcessor = DomainProcessor(enabled=True)
    native_tags_processor: NativeTagsProcessor = NativeTagsProcessor(enabled=True)
    openai_chat_35_processor: OpenAIChat35Processor = OpenAIChat35Processor()
    openai_chat_35_processor_functions: OpenAIChat35ProcessorFunctions = OpenAIChat35ProcessorFunctions()

    class Config:
        env_prefix = "FFUN_LIBRARIAN_"


settings = Settings()
