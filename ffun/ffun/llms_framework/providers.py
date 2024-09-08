from ffun.core.register import Entity, Register
from ffun.google.provider_interface import provider as google_provider
from ffun.llms_framework.entities import LLMProvider
from ffun.llms_framework.provider_interface import ProviderInterface, provider_test
from ffun.openai.provider_interface import provider as openai_provider


class Value(Entity):
    def __init__(self, key: str, provider: ProviderInterface) -> None:
        super().__init__(key=key)
        self.provider = provider


LLMProviders = Register[Value]

llm_providers: LLMProviders = Register()

llm_providers.add(Value(LLMProvider.test, provider_test))
llm_providers.add(Value(LLMProvider.openai, openai_provider))
llm_providers.add(Value(LLMProvider.google, google_provider))
