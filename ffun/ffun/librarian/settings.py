import pydantic
import pydantic_settings

from ffun.core.settings import BaseSettings


class BaseProcessor(pydantic.BaseModel):
    enabled: bool = False
    workers: int = 1


class DomainProcessor(BaseProcessor):
    pass


class NativeTagsProcessor(BaseProcessor):
    pass


class UpperCaseTitleProcessor(BaseProcessor):
    pass


# TODO: will be ranamed & refactored in gh-227
class OpenAIChat35Processor(BaseProcessor):
    model: str = "gpt-4o-mini-2024-07-18"


# TODO: will be removed in gh-227
class OpenAIChat35FunctionsProcessor(BaseProcessor):
    model: str = "gpt-4o-mini-2024-07-18"


class Settings(BaseSettings):
    domain_processor: DomainProcessor = DomainProcessor(enabled=True)
    native_tags_processor: NativeTagsProcessor = NativeTagsProcessor(enabled=True)
    upper_case_title_processor: UpperCaseTitleProcessor = UpperCaseTitleProcessor(enabled=True)

    openai_chat_35_processor: OpenAIChat35Processor = OpenAIChat35Processor()
    openai_chat_35_functions_processor: OpenAIChat35FunctionsProcessor = OpenAIChat35FunctionsProcessor()

    model_config = pydantic_settings.SettingsConfigDict(env_prefix="FFUN_LIBRARIAN_")


settings = Settings()
