import contextlib
import functools
from typing import Generator, Sequence

import openai
import tiktoken
from openai.types.chat import ChatCompletionMessageParam

from ffun.core import logging
from ffun.llms_framework import domain as llmsf_domain
from ffun.llms_framework import errors as llmsf_errors
from ffun.llms_framework.entities import KeyStatus, LLMConfiguration, LLMProvider
from ffun.llms_framework.keys_statuses import Statuses
from ffun.llms_framework.provider_interface import ChatRequest, ChatResponse, ProviderInterface
from ffun.openai.settings import settings

logger = logging.get_module_logger()


class OpenAIChatRequest(ChatRequest):
    messages: list[ChatCompletionMessageParam]


def _client(api_key: str) -> openai.AsyncOpenAI:
    return openai.AsyncOpenAI(api_key=api_key, base_url=settings.api_entry_point, timeout=settings.api_timeout)


class OpenAIChatResponse(ChatResponse):
    content: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int

    def response_content(self) -> str:
        return self.content

    def input_tokens(self) -> int:
        return self.prompt_tokens

    def output_tokens(self) -> int:
        return self.completion_tokens


@functools.cache
def _get_encoding(model: str) -> tiktoken.Encoding:
    return tiktoken.encoding_for_model(model)


@contextlib.contextmanager
def track_key_status(key: str, statuses: Statuses) -> Generator[None, None, None]:
    try:
        yield
        statuses.set(key, KeyStatus.works)
    except openai.AuthenticationError:
        statuses.set(key, KeyStatus.broken)
        raise
    except openai.RateLimitError:
        statuses.set(key, KeyStatus.quota)
        raise
    except openai.PermissionDeniedError:
        statuses.set(key, KeyStatus.broken)
        raise
    except openai.APIError:
        statuses.set(key, KeyStatus.unknown)
        raise


# TODO: tests
class OpenAIInterface(ProviderInterface):
    provider = LLMProvider.openai

    additional_tokens_per_message: int = 10

    def estimate_tokens(self, config: LLMConfiguration, text: str) -> int:
        encoding = _get_encoding(config.model)

        system_tokens = (
            self.additional_tokens_per_message + len(encoding.encode("system")) + len(encoding.encode(config.system))
        )

        text_tokens = self.additional_tokens_per_message + len(encoding.encode("user")) + len(encoding.encode(text))

        return system_tokens + text_tokens

    async def chat_request(  # type: ignore
        self, config: LLMConfiguration, api_key: str, request: OpenAIChatRequest
    ) -> OpenAIChatResponse:
        try:
            with track_key_status(api_key, self.api_keys_statuses):
                answer = await _client(api_key=api_key).chat.completions.create(
                    model=config.model,
                    temperature=float(config.temperature),
                    max_tokens=config.max_return_tokens,
                    top_p=float(config.top_p),
                    presence_penalty=float(config.presence_penalty),
                    frequency_penalty=float(config.frequency_penalty),
                    messages=request.messages,
                )
        except openai.APIError as e:
            logger.info("openai_api_error", message=str(e))
            raise llmsf_errors.TemporaryError(message=str(e)) from e

        logger.info("openai_response")

        assert answer.choices[0].message.content is not None
        assert answer.usage is not None

        content = answer.choices[0].message.content

        return OpenAIChatResponse(
            content=content,
            prompt_tokens=answer.usage.prompt_tokens,
            completion_tokens=answer.usage.completion_tokens,
            total_tokens=answer.usage.total_tokens,
        )

    def prepare_requests(self, config: LLMConfiguration, text: str) -> Sequence[OpenAIChatRequest]:

        parts = llmsf_domain.split_text_according_to_tokens(llm=self, llm_config=config, text=text)

        requests = []

        for part in parts:
            request = OpenAIChatRequest(
                messages=[{"role": "system", "content": config.system}, {"role": "user", "content": part}]
            )

            requests.append(request)

        return requests

    async def check_api_key(self, config: LLMConfiguration, api_key: str) -> KeyStatus:
        with track_key_status(api_key, self.api_keys_statuses):
            try:
                await _client(api_key=api_key).models.list()
            except openai.APIError:
                pass

        return self.api_keys_statuses.get(api_key)


provider = OpenAIInterface()
