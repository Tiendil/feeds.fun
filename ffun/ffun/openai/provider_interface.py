import async_lru
import functools
import json
import tiktoken
from typing import Any

from ffun.core import logging
from ffun.llms_framework.entities import LLMConfiguration
from ffun.llms_framework.provider_interface import ProviderInterface, ChatRequest, ChatResponse
from ffun.llms_framework import errors as llmsf_errors
from ffun.llms_framework import domain as llmsf_domain
from ffun.openai.entities import OpenAIModelInfo
from ffun.openai.keys_statuses import statuses, track_key_status
from ffun.openai import errors
import openai

logger = logging.get_module_logger()


# TODO: move to configs
# TODO: add
_models = [
    OpenAIModelInfo(name="gpt-4o-mini-2024-07-18", max_context_size=128000, max_return_tokens=16384)
]


class OpenAIChatRequest(ChatRequest):
    messages = list[dict[str, str]]


class OpenAIChatResponse(ChatResponse):
    content: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


@functools.cache
def _get_encoding(model: str) -> tiktoken.Encoding:
    return tiktoken.encoding_for_model(model)


# TODO: tests
class OpenAIInterface(ProviderInterface):

    # TODO: add @functools.cache (but remember about `self`)
    def _get_model(self, config: LLMConfiguration) -> OpenAIModelInfo:
        for m in _models:
            if m.name == config.model:
                return m

        raise llmsf_errors.ModelDoesNotFound(model=config.model)

    def max_context_size_for_model(self, config: LLMConfiguration) -> int:
        return self._get_model(config).max_context_size

    def max_return_tokens_for_model(self, config: LLMConfiguration) -> int:
        return self._get_model(config).max_return_tokens

    def is_model_supported(self, model: str) -> bool:
        try:
            self._get_model(model)
            return True
        except llmsf_errors.ModelDoesNotFound:
            return False

    def estimate_tokens(self, config: LLMConfiguration, text: str) -> int:
        encoding = _get_encoding(config.model)

        system_tokens = config.additional_tokens_per_message + len(encoding.encode("system")) + len(encoding.encode(config.system))

        text_tokens = config.additional_tokens_per_message + len(encoding.encode("user")) + len(encoding.encode(text))

        return system_tokens + text_tokens

    async def chat_request(self, config: LLMConfiguration, api_key: str, request: OpenAIChatRequest) -> OpenAIChatResponse:
        # TODO: how to differe keys of different providers?
        # TODO: move out of here

        try:
            with track_key_status(api_key):
                # TODO: cache client
                # TODO: add automatic retries
                answer = await openai.AsyncOpenAI(api_key=api_key).chat.completions.create(
                    model=config.model,
                    temperature=config.temperature,
                    max_tokens=config.max_return_tokens,
                    top_p=config.top_p,
                    presence_penalty=config.presence_penalty,
                    frequency_penalty=config.frequency_penalty,
                    messages=request.messages,
                )
        except openai.APIError as e:
            logger.info("openai_api_error", message=str(e))
            raise errors.TemporaryError(message=str(e)) from e

        logger.info("openai_response")

        assert answer.choices[0].message.content is not None
        assert answer.usage is not None

        content = answer.choices[0].message.content

        return OpenAIChatResponse(content=content,
                                  prompt_tokens=answer.usage.prompt_tokens,
                                  completion_tokens=answer.usage.completion_tokens,
                                  total_tokens=answer.usage.total_tokens)

    def prepare_requests(self,  # noqa: CFQ002
                         config: LLMConfiguration,
                         text: str) -> list[OpenAIChatRequest]:

        parts = llmsf_domain.split_text_according_to_tokens(llm=self,
                                                            config=config,
                                                            text=text)

        requests = []

        for part in parts:
            request = OpenAIChatRequest(messages=[{"role": "system", "content": config.system},
                                                  {"role": "user", "content": part}])

            requests.append(request)

        return requests


provider = OpenAIInterface()
