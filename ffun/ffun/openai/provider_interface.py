import contextlib
import functools
from typing import Any, Generator, Sequence

import openai
import tiktoken

from ffun.core import logging
from ffun.llms_framework import domain as llmsf_domain
from ffun.llms_framework import errors as llmsf_errors
from ffun.llms_framework.entities import KeyStatus, LLMConfiguration, LLMProvider
from ffun.llms_framework.keys_statuses import Statuses
from ffun.llms_framework.provider_interface import ChatRequest, ChatResponse, ProviderInterface
from ffun.openai.settings import settings

logger = logging.get_module_logger()


class OpenAIChatRequest(ChatRequest):
    system: str
    user: str


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

    async def chat_request(  # noqa: CCR001
        self, config: LLMConfiguration, api_key: str, request: OpenAIChatRequest  # type: ignore
    ) -> OpenAIChatResponse:
        try:
            tool_used = False

            # TODO: if would be nice to specify for each model which parameters are supported
            #       but for now it is too much work
            attributes: dict[str, Any] = {
                "store": False,
                "model": config.model,
                "max_output_tokens": config.max_return_tokens,
                "instructions": request.system,
                "input": request.user,
            }

            if config.temperature is not None:
                attributes["temperature"] = float(config.temperature)

            if config.top_p is not None:
                attributes["top_p"] = float(config.top_p)

            if config.verbosity is not None:
                if "text" not in attributes:
                    attributes["text"] = {}

                attributes["text"]["verbosity"] = config.verbosity

            if config.reasoning_effort is not None:
                if "reasoning" not in attributes:
                    attributes["reasoning"] = {}

                attributes["reasoning"]["effort"] = config.reasoning_effort

            if config.lark_grammar is not None:
                tool_used = True
                tool_name = "FEEDS_FUN_TAGS_GRAMMAR"  # TODO: move to configs?
                attributes["tool_choice"] = {"type": "custom", "name": tool_name}
                attributes["tools"] = [
                    {
                        "type": "custom",
                        "name": tool_name,
                        "description": config.lark_description or "Register tags into Feeds Fun service.",
                        "format": {"type": "grammar", "syntax": "lark", "definition": config.lark_grammar},
                    },
                ]

            with track_key_status(api_key, self.api_keys_statuses):
                answer = await _client(api_key=api_key).responses.create(**attributes)
        except openai.APIError as e:
            message = str(e)
            logger.info("openai_api_error", message=message)
            raise llmsf_errors.TemporaryError(message=message) from e

        logger.info("openai_response")

        assert answer.usage is not None
        assert answer.output is not None

        content = None

        if tool_used:
            for output in answer.output:
                if output.type == "custom_tool_call":
                    content = output.input
                    break
        else:
            content = answer.output_text

        if content is None:
            logger.error("openai_no_output", answer=repr(answer))
            raise llmsf_errors.TemporaryError(message="Could not get output from OpenAI response")

        return OpenAIChatResponse(
            content=content,
            prompt_tokens=answer.usage.input_tokens,
            completion_tokens=answer.usage.output_tokens,
            total_tokens=answer.usage.total_tokens,
        )

    def prepare_requests(self, config: LLMConfiguration, text: str) -> Sequence[OpenAIChatRequest]:

        parts = llmsf_domain.split_text_according_to_tokens(llm=self, llm_config=config, text=text)

        requests = []

        for part in parts:
            request = OpenAIChatRequest(
                system=config.system,
                user=part,
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
