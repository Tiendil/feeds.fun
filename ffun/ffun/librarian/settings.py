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
    model: str = 'gpt-3.5-turbo-16k-0613'


class OpenAIChat35FunctionsProcessor(BaseProcessor):  # type: ignore
    model: str = 'gpt-3.5-turbo-16k-0613'


class Settings(BaseSettings):  # type: ignore
    domain_processor: DomainProcessor = DomainProcessor(enabled=True)
    native_tags_processor: NativeTagsProcessor = NativeTagsProcessor(enabled=True)
    openai_chat_35_processor: OpenAIChat35Processor = OpenAIChat35Processor()
    openai_chat_35_functions_processor: OpenAIChat35FunctionsProcessor = OpenAIChat35FunctionsProcessor()

    class Config:
        env_prefix = "FFUN_LIBRARIAN_"


settings = Settings()
