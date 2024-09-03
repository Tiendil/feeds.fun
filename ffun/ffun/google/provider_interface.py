import contextlib
import functools
from typing import Generator

from ffun.core import logging
from ffun.llms_framework import domain as llmsf_domain
from ffun.llms_framework import errors as llmsf_errors
from ffun.llms_framework.entities import KeyStatus, LLMConfiguration, Provider
from ffun.llms_framework.keys_statuses import Statuses
from ffun.llms_framework.provider_interface import ChatRequest, ChatResponse, ProviderInterface

logger = logging.get_module_logger()


# class GoogleChatRequest(ChatRequest):
#     messages: list[ChatCompletionMessageParam]


class GoogleChatResponse(ChatResponse):
    content: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int

    def response_content(self) -> str:
        return self.content

    def spent_tokens(self) -> int:
        return self.total_tokens


# @functools.cache
# def _get_encoding(model: str) -> tiktoken.Encoding:
#     return tiktoken.encoding_for_model(model)


# TODO: tests
# TODO: separate keys by providers
# @contextlib.contextmanager
# def track_key_status(key: str, statuses: Statuses) -> Generator[None, None, None]:
#     try:
#         yield
#         statuses.set(key, KeyStatus.works)
#     except google.AuthenticationError:
#         statuses.set(key, KeyStatus.broken)
#         raise
#     except google.RateLimitError:
#         statuses.set(key, KeyStatus.quota)
#         raise
#     except google.PermissionDeniedError:
#         statuses.set(key, KeyStatus.broken)
#         raise
#     except google.APIError:
#         statuses.set(key, KeyStatus.unknown)
#         raise


# TODO: tests
class GoogleInterface(ProviderInterface):
    provider = Provider.google

#     def estimate_tokens(self, config: LLMConfiguration, text: str) -> int:
#         encoding = _get_encoding(config.model)

#         system_tokens = (
#             config.additional_tokens_per_message + len(encoding.encode("system")) + len(encoding.encode(config.system))
#         )

#         text_tokens = config.additional_tokens_per_message + len(encoding.encode("user")) + len(encoding.encode(text))

#         return system_tokens + text_tokens

#     async def chat_request(  # type: ignore
#         self, config: LLMConfiguration, api_key: str, request: GoogleChatRequest
#     ) -> GoogleChatResponse:
#         # TODO: how to differe keys of different providers?
#         # TODO: move out of here

#         try:
#             with track_key_status(api_key, self.api_keys_statuses):
#                 # TODO: cache client
#                 # TODO: add automatic retries
#                 answer = await google.AsyncGoogle(api_key=api_key).chat.completions.create(
#                     model=config.model,
#                     temperature=float(config.temperature),
#                     max_tokens=config.max_return_tokens,
#                     top_p=float(config.top_p),
#                     presence_penalty=float(config.presence_penalty),
#                     frequency_penalty=float(config.frequency_penalty),
#                     messages=request.messages,
#                 )
#         except google.APIError as e:
#             logger.info("google_api_error", message=str(e))
#             raise llmsf_errors.TemporaryError(message=str(e)) from e

#         logger.info("google_response")

#         assert answer.choices[0].message.content is not None
#         assert answer.usage is not None

#         content = answer.choices[0].message.content

#         return GoogleChatResponse(
#             content=content,
#             prompt_tokens=answer.usage.prompt_tokens,
#             completion_tokens=answer.usage.completion_tokens,
#             total_tokens=answer.usage.total_tokens,
#         )

#     def prepare_requests(self, config: LLMConfiguration, text: str) -> list[GoogleChatRequest]:  # type: ignore  # noqa: CFQ002

#         parts = llmsf_domain.split_text_according_to_tokens(llm=self, config=config, text=text)

#         requests = []

#         for part in parts:
#             request = GoogleChatRequest(
#                 messages=[{"role": "system", "content": config.system}, {"role": "user", "content": part}]
#             )

#             requests.append(request)

#         return requests

#     async def check_api_key(self, config: LLMConfiguration, api_key: str) -> KeyStatus:
#         with track_key_status(api_key, self.api_keys_statuses):
#             try:
#                 await google.AsyncGoogle(api_key=api_key).models.list()
#             except google.APIError:
#                 pass

#         return self.api_keys_statuses.get(api_key)


# provider = GoogleInterface()
