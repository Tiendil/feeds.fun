
from ffun.core.entities import BaseEntity


class ChatRequest(BaseEntity):
    pass


class ChatResponse(BaseEntity):
    pass


class ProviderInterface:

    def max_context_size_for_model(self, model: str) -> int:
        raise NotImplementedError

    def max_return_tokens_for_model(self, model: str) -> int:
        raise NotImplementedError

    def is_model_supported(self, model: str) -> bool:
        raise NotImplementedError

    def estimate_tokens(self, model: str, system: str, text: str, function: str | None = None) -> int:
        raise NotImplementedError

    async def chat_request(self, model: str, api_key: str, request: ChatRequest) -> ChatResponse:
        raise NotImplementedError
