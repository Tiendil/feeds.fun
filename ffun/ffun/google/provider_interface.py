import contextlib
import functools
from typing import Generator
# import google.generativeai as genai
# from google.ai import generativelanguage as glm
# from google.generativeai.types import helper_types
# from google.generativeai.types import safety_types
# from google.api_core import exceptions as google_core_exceptions
from ffun.core import logging
from ffun.llms_framework import domain as llmsf_domain
from ffun.llms_framework import errors as llmsf_errors
from ffun.llms_framework.entities import KeyStatus, LLMConfiguration, Provider
from ffun.llms_framework.keys_statuses import Statuses
from ffun.llms_framework.provider_interface import ChatRequest, ChatResponse, ProviderInterface
# from vertexai.preview.tokenization import get_tokenizer_for_model
from ffun.google.client import Client
from ffun.google.entities import GoogleChatRequest, GoogleChatResponse, ChatMessage, GenerationConfig

logger = logging.get_module_logger()

# IMPROTANT!!!
# TODO: Solve conflict with using different providers by users vs lack of using providers by system logic (collections)
#       There is possible situation when collections uses one provider and ignore another, but user wants to use another provider
#       This may lead to processing all feeds in collections with the user key
#       Maybe it is better to restrict processing of collections with user keys
#       Maybe, we could move flags: for_collections, for_users, for_all to the configuration of all tag processors?


# TODO: tests
# TODO: separate keys by providers
@contextlib.contextmanager
def track_key_status(key: str, statuses: Statuses) -> Generator[None, None, None]:
    try:
        yield
        statuses.set(key, KeyStatus.works)
    # TODO: add correct processing
    # except google_core_exceptions.InvalidArgument as e:
    #     if e.reason == 'API_KEY_INVALID':
    #         statuses.set(key, KeyStatus.broken)
    #     else:
    #         statuses.set(key, KeyStatus.unknown)

    #     raise

    # except google_core_exceptions.TooManyRequests:
    #     statuses.set(key, KeyStatus.quota)
    #     raise

    # except google_core_exceptions.GoogleAPIError:
    #     statuses.set(key, KeyStatus.unknown)
    #     raise

    except Exception:
        statuses.set(key, KeyStatus.unknown)
        raise


# TODO: add to the documentation note about quotas of Gemini API (especially free tier)
# TODO: tests
# TODO: test support of multiple keys
class GoogleInterface(ProviderInterface):
    provider = Provider.google

    # TODO: refactor according to gemini logic
    def estimate_tokens(self, config: LLMConfiguration, text: str) -> int:
        # TODO: do better
        return len(text) * 4
        # tokenizer = get_tokenizer_for_model(config.model)

        # system_tokens = [config.additional_tokens_per_message,
        #                  tokenizer.count_tokens("system").total_tokens,
        #                  tokenizer.count_tokens(config.system).total_tokens]

        # text_tokens = [config.additional_tokens_per_message,
        #                tokenizer.count_tokens("user").total_tokens,
        #                tokenizer.count_tokens(text).total_tokens]

        # return sum(system_tokens) + sum(text_tokens)

    async def chat_request(  # type: ignore
        self, config: LLMConfiguration, api_key: str, request: GoogleChatRequest
    ) -> GoogleChatResponse:

        # TODO: cache
        client = Client(api_key=api_key)

        generation_config = GenerationConfig(max_output_tokens=config.max_return_tokens,
                                             temperature=float(config.temperature),
                                             top_p=float(config.top_p),
                                             top_k=None)

        try:
            with track_key_status(api_key, self.api_keys_statuses):
                # TODO: retries via request_options?
                answer = await client.generate_content(model=config.model,
                                                       request=request,
                                                       config=generation_config)

        # TODO: add correct error processing
        # except google.APIError as e:
        except Exception as e:
            print(e.__class__, e)
            logger.info("google_api_error", message=str(e))
            raise llmsf_errors.TemporaryError(message=str(e)) from e

        logger.info("google_response")

        return answer

    def prepare_requests(self, config: LLMConfiguration, text: str) -> list[GoogleChatRequest]:  # type: ignore  # noqa: CFQ002
        parts = llmsf_domain.split_text_according_to_tokens(llm=self, config=config, text=text)

        requests = []

        for part in parts:
            request = GoogleChatRequest(
                system=ChatMessage(text=config.system),
                messages=[ChatMessage(role='user', text=part)]
            )

            requests.append(request)

        return requests

    async def check_api_key(self, config: LLMConfiguration, api_key: str) -> KeyStatus:
        # TODO: implement actual check
        with track_key_status(api_key, self.api_keys_statuses):
            pass
        #     try:
        #         await google.AsyncGoogle(api_key=api_key).models.list()
        #     except google.APIError:
        #         pass

        return self.api_keys_statuses.get(api_key)


provider = GoogleInterface()
