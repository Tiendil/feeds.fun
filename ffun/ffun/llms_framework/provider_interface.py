from typing import Sequence

from ffun.llms_framework import errors
from ffun.llms_framework.entities import ChatRequest, ChatResponse, KeyStatus, LLMConfiguration, LLMProvider, ModelInfo
from ffun.llms_framework.keys_statuses import Statuses
from ffun.llms_framework.settings import settings


class ProviderInterface:

    provider: LLMProvider = NotImplemented

    def __init__(self) -> None:
        self.api_keys_statuses = Statuses()

    def get_model(self, config: LLMConfiguration) -> ModelInfo:
        for m in settings.models:
            if m.provider != self.provider:
                continue

            if m.name == config.model:
                return m

        raise errors.ModelDoesNotFound(model=config.model)

    def prepare_requests(self, config: LLMConfiguration, text: str) -> Sequence[ChatRequest]:
        raise NotImplementedError("Must be implemented in a subclass")

    def estimate_tokens(self, config: LLMConfiguration, text: str) -> int:
        raise NotImplementedError("Must be implemented in a subclass")

    async def chat_request(self, config: LLMConfiguration, api_key: str, request: ChatRequest) -> ChatResponse:
        raise NotImplementedError("Must be implemented in a subclass")

    async def check_api_key(self, config: LLMConfiguration, api_key: str) -> KeyStatus:
        raise NotImplementedError("Must be implemented in a subclass")


class ChatRequestTest(ChatRequest):
    text: str


class ChatResponseTest(ChatResponse):
    content: str

    def response_content(self) -> str:
        return self.content

    def input_tokens(self) -> int:
        return len(self.content)

    # TODO: make it differ from input_tokens
    def output_tokens(self) -> int:
        return len(self.content)


class ProviderTest(ProviderInterface):
    provider = LLMProvider.test

    def prepare_requests(self, config: LLMConfiguration, text: str) -> Sequence[ChatRequestTest]:  # type: ignore
        return [ChatRequestTest(text=text)]

    def estimate_tokens(self, config: LLMConfiguration, text: str) -> int:
        """Count each character as a token to simplify tests"""
        return len(text)

    async def chat_request(  # type: ignore
        self, config: LLMConfiguration, api_key: str, request: ChatRequestTest
    ) -> ChatResponseTest:
        return ChatResponseTest(content=request.text)

    async def check_api_key(self, config: LLMConfiguration, api_key: str) -> KeyStatus:
        return KeyStatus.works


provider_test = ProviderTest()
