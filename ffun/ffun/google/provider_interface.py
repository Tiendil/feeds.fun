import contextlib
import functools
from typing import Generator
import google.generativeai as genai
from google.ai import generativelanguage as glm
from google.generativeai.types import helper_types
from google.generativeai.types import safety_types
from ffun.core import logging
from ffun.llms_framework import domain as llmsf_domain
from ffun.llms_framework import errors as llmsf_errors
from ffun.llms_framework.entities import KeyStatus, LLMConfiguration, Provider
from ffun.llms_framework.keys_statuses import Statuses
from ffun.llms_framework.provider_interface import ChatRequest, ChatResponse, ProviderInterface
from vertexai.preview.tokenization import get_tokenizer_for_model

logger = logging.get_module_logger()

# IMPROTANT!!!
# TODO: Solve conflict with using different providers by users vs lack of using providers by system logic (collections)
#       There is possible situation when collections uses one provider and ignore another, but user wants to use another provider
#       This may lead to processing all feeds in collections with the user key
#       Maybe it is better to restrict processing of collections with user keys


class GoogleChatRequest(ChatRequest):
    system_message: str
    user_message: str


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
@contextlib.contextmanager
def track_key_status(key: str, statuses: Statuses) -> Generator[None, None, None]:
    try:
        yield
        statuses.set(key, KeyStatus.works)
    # TODO: uncomment concrete exceptions
    #       remove this one
    except Exception:
        statuses.set(key, KeyStatus.broken)
        raise
    # except google.AuthenticationError:
    #     statuses.set(key, KeyStatus.broken)
    #     raise
    # except google.RateLimitError:
    #     statuses.set(key, KeyStatus.quota)
    #     raise
    # except google.PermissionDeniedError:
    #     statuses.set(key, KeyStatus.broken)
    #     raise
    # except google.APIError:
    #     statuses.set(key, KeyStatus.unknown)
    #     raise


# TODO: add to the documentation note about quotas of Gemini API (especially free tier)
# TODO: tests
# TODO: test support of multiple keys
class GoogleInterface(ProviderInterface):
    provider = Provider.google

    # TODO: refactor according to gemini logic
    def estimate_tokens(self, config: LLMConfiguration, text: str) -> int:
        tokenizer = get_tokenizer_for_model(config.model)

        system_tokens = [config.additional_tokens_per_message,
                         tokenizer.count_tokens("system").total_tokens,
                         tokenizer.count_tokens(config.system).total_tokens]

        text_tokens = [config.additional_tokens_per_message,
                       tokenizer.count_tokens("user").total_tokens,
                       tokenizer.count_tokens(text).total_tokens]

        return sum(system_tokens) + sum(text_tokens)

    # TODO: test
    # TODO: Code is taken from https://github.com/google-gemini/generative-ai-python/issues/136
    #       Refactor after this issue will be resolved
    def _model(self, model_name: str, system: str, api_key: str) -> genai.GenerativeModel:
        # TODO: cache clients?
        client = glm.GenerativeServiceClient(
            client_options={'api_key': api_key}
        )

        model = genai.GenerativeModel(model_name=model_name,
                                      system_instruction=system)
        model._client = client

        return model

    async def chat_request(  # type: ignore
        self, config: LLMConfiguration, api_key: str, request: GoogleChatRequest
    ) -> GoogleChatResponse:
        # TODO: how to differe keys of different providers?
        # TODO: move out of here

        model = self._model(model_name=config.model,
                            system=request.system_message,
                            api_key=api_key)

        generation_config = genai.types.GenerationConfig(
            candidate_count=1,
            stop_sequences=[],
            response_mime_type='text/plain',
            response_schema=None,
            max_output_tokens=config.max_return_tokens,
            temperature=config.temperature,
            top_p=config.top_p,
            top_k=None,  # TODO: add to config?
        ),

        safety_settings = []

        for category in safety_types.HarmCategory:
            safety_settings.append(
                safety_types.SafetySetting(
                    category=category,
                    threshold=safety_types.HarmBlockThreshold.BLOCK_NONE,
                )
            )

        try:
            with track_key_status(api_key, self.api_keys_statuses):
                # TODO: retries via request_options?
                answer = await model.generate_content_async(request.user_message,
                                                            generation_config=generation_config,
                                                            safety_settings=safety_settings)

                print(answer)

        # TODO: add correct error processing
        # except google.APIError as e:
        except Exception as e:
            logger.info("google_api_error", message=str(e))
            raise llmsf_errors.TemporaryError(message=str(e)) from e

        logger.info("google_response")

        # assert answer.choices[0].message.content is not None
        # assert answer.usage is not None

        content = answer.choices[0].message.content

        return GoogleChatResponse(
            content=content,
            prompt_tokens=answer.usage.prompt_tokens,
            completion_tokens=answer.usage.completion_tokens,
            total_tokens=answer.usage.total_tokens,
        )

    def prepare_requests(self, config: LLMConfiguration, text: str) -> list[GoogleChatRequest]:  # type: ignore  # noqa: CFQ002

        parts = llmsf_domain.split_text_according_to_tokens(llm=self, config=config, text=text)

        requests = []

        for part in parts:
            request = GoogleChatRequest(
                system_message=config.system,
                user_message=part
            )

            requests.append(request)

        return requests

#     async def check_api_key(self, config: LLMConfiguration, api_key: str) -> KeyStatus:
#         with track_key_status(api_key, self.api_keys_statuses):
#             try:
#                 await google.AsyncGoogle(api_key=api_key).models.list()
#             except google.APIError:
#                 pass

#         return self.api_keys_statuses.get(api_key)


# provider = GoogleInterface()
