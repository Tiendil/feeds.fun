import async_lru
import functools
import json
import tiktoken
from typing import Any

from ffun.llms_framework.provider_interface import ProviderInterface, ChatRequest, ChatResponse
from ffun.llms_framework import errors as llmsf_errors
from ffun.llms_framework import domain as llmsf_domain
from ffun.openai.entities import OpenAIModelInfo
from ffun.openai.keys_statuses import statuses, track_key_status
from openai import AsyncOpenAI


# TODO: move to configs
# TODO: add
_models = [
    OpenAIModelInfo(name="gpt-4o-mini-2024-07-18", max_context_size=128000, max_return_tokens=16384)
]

# TODO: move to model info?
_additional_tokens_per_message = 10


class OpenAIChatRequest(ChatRequest):
    messages = list[dict[str, str]]


class OpenAIChatResponse(ChatResponse):
    pass


@functools.cache
def _get_encoding(model: str) -> tiktoken.Encoding:
    return tiktoken.encoding_for_model(model)


# TODO: tests
class OpenAIInterface(ProviderInterface):

    # TODO: add @functools.cache (but remember about `self`)
    def _get_model(self, model: str) -> OpenAIModelInfo:
        for m in _models:
            if m.name == model:
                return m

        raise llmsf_errors.ModelDoesNotFound(model=model)

    def max_context_size_for_model(self, model: str) -> int:
        return self._get_model(model).max_context_size

    def max_return_tokens_for_model(self, model: str) -> int:
        return self._get_model(model).max_return_tokens

    def is_model_supported(self, model: str) -> bool:
        try:
            self._get_model(model)
            return True
        except llmsf_errors.ModelDoesNotFound:
            return False

    def estimate_tokens(self, model: str, system: str, text: str) -> int:
        encoding = _get_encoding(model)

        system_tokens = _additional_tokens_per_message + len(encoding.encode("system")) + len(encoding.encode(system))

        text_tokens = _additional_tokens_per_message + len(encoding.encode("user")) + len(encoding.encode(text))

        return system_tokens + text_tokens

    async def chat_request(self, model: str, api_key: str, request: OpenAIChatRequest) -> OpenAIChatResponse:
        arguments: dict[str, Any] = {}

        # TODO: how to differe keys of different providers?
        with track_key_status(api_key):
            try:
                answer = await AsyncOpenAI(api_key=api_key).chat.completions.create(
                    model=model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    top_p=top_p,
                    presence_penalty=presence_penalty,
                    frequency_penalty=frequency_penalty,
                    messages=messages,  # type: ignore
                    **arguments
                )
            except openai.APIError as e:
                logger.info("openai_api_error", message=str(e))
                raise errors.TemporaryError(message=str(e)) from e

        logger.info("openai_response")

        if function:
            assert answer.choices[0].message.function_call is not None
            content = answer.choices[0].message.function_call.arguments
        else:
            assert answer.choices[0].message.content is not None
            content = answer.choices[0].message.content

        assert answer.usage is not None

        return entities.OpenAIAnswer(
            content=content,
            prompt_tokens=answer.usage.prompt_tokens,
            completion_tokens=answer.usage.completion_tokens,
            total_tokens=answer.usage.total_tokens,
        )

    # TODO: move to interface?
    async def prepare_requests(self,  # noqa: CFQ002
                               model: str,
                               system: str,
                               text: str,
                               max_return_tokens: int,
                               intersection: int) -> list[OpenAIChatRequest]:

        parts_number = 0

        max_context_size = self.max_context_size_for_model(model)

        # TODO: move to common code
        while True:
            parts_number += 1

            parts = llmsf_domain.split_text(text, parts=parts_number, intersection=intersection)

            parts_tokens = [self.estimate_tokens(model,
                                                 system=system,
                                                 text=part) for part in parts]

            if any(tokens + max_return_tokens >= max_context_size for tokens in parts_tokens):
                continue

            # if sum(tokens + max_return_tokens for tokens in parts_tokens) >= max_context_size:
            #     break

        requests = []

        for part in parts:
            request = OpenAIChatRequest(messages=[{"role": "system", "content": system},
                                                  {"role": "user", "content": part}])

            requests.append(request)

        return requests
