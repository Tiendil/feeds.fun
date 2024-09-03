from ffun.llms_framework import errors
from ffun.llms_framework.entities import KeyStatus, LLMConfiguration, ModelInfo, Provider, ChatRequest, ChatResponse
from ffun.llms_framework.keys_statuses import Statuses
from ffun.llms_framework.settings import settings


# TODO: tests
class ProviderInterface:

    provider: Provider = NotImplemented

    def __init__(self) -> None:
        self.api_keys_statuses = Statuses()

    # TODO: add @functools.cache (but remember about `self`)
    def _get_model(self, config: LLMConfiguration) -> ModelInfo:
        for m in settings.models:
            if m.provider != self.provider:
                continue

            if m.name == config.model:
                return m

        raise errors.ModelDoesNotFound(model=config.model)

    def max_context_size_for_model(self, config: LLMConfiguration) -> int:
        return self._get_model(config).max_context_size

    def max_return_tokens_for_model(self, config: LLMConfiguration) -> int:
        return self._get_model(config).max_return_tokens

    def is_model_supported(self, config: LLMConfiguration) -> bool:
        try:
            self._get_model(config)
            return True
        except errors.ModelDoesNotFound:
            return False

    def estimate_tokens(self, config: LLMConfiguration, text: str) -> int:
        raise NotImplementedError("Must be implemented in a subclass")

    async def chat_request(self, config: LLMConfiguration, api_key: str, request: ChatRequest) -> ChatResponse:
        raise NotImplementedError("Must be implemented in a subclass")

    async def check_api_key(self, config: LLMConfiguration, api_key: str) -> KeyStatus:
        raise NotImplementedError("Must be implemented in a subclass")
