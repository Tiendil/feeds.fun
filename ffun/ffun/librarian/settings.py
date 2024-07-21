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


class OpenAIGeneralProcessor(BaseProcessor):
    model: str = "gpt-4o-mini-2024-07-18"


# TODO: will be removed in gh-227
class OpenAIChat35FunctionsProcessor(BaseProcessor):
    model: str = "gpt-4o-mini-2024-07-18"


class Settings(BaseSettings):
    domain_processor: DomainProcessor = DomainProcessor(enabled=True)
    native_tags_processor: NativeTagsProcessor = NativeTagsProcessor(enabled=True)
    upper_case_title_processor: UpperCaseTitleProcessor = UpperCaseTitleProcessor(enabled=True)

    openai_general_processor: OpenAIGeneralProcessor = OpenAIGeneralProcessor()

    model_config = pydantic_settings.SettingsConfigDict(env_prefix="FFUN_LIBRARIAN_")


settings = Settings()
