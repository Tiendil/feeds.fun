from ffun.core.register import Entity, Register
from ffun.llms_framework.entities import Provider
from ffun.llms_framework.provider_interface import ProviderInterface, provider_test
from ffun.openai.provider_interface import provider as openai_provider


class Value(Entity):
    def __init__(self, key: str, provider: ProviderInterface) -> None:
        super().__init__(key=key)
        self.provider = provider


LLMProviders = Register[Value]

llm_providers: LLMProviders = Register()

llm_providers.add(Value(Provider.test, provider_test))
llm_providers.add(Value(Provider.openai, openai_provider))
