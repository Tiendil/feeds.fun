import contextlib
from typing import Generator, Sequence

from ffun.core import logging
from ffun.google import errors
from ffun.google.client import Client
from ffun.google.entities import ChatMessage, GenerationConfig, GoogleChatRequest, GoogleChatResponse
from ffun.llms_framework import domain as llmsf_domain
from ffun.llms_framework import errors as llmsf_errors
from ffun.llms_framework.entities import KeyStatus, LLMConfiguration, LLMProvider
from ffun.llms_framework.keys_statuses import Statuses
from ffun.llms_framework.provider_interface import ProviderInterface

logger = logging.get_module_logger()

# Important!!!
# TODO: allow specifying providers as third-party plugins
#       or create an issue on github about that

# IMPROTANT!!!
# TODO: Solve conflict with using different providers by users vs lack of using providers by system logic (collections)
#       There is possible situation when collections uses one provider and ignore another,
#       but user wants to use another provider
#       This may lead to processing all feeds in collections with the user key
#       Maybe it is better to restrict processing of collections with user keys
#       Maybe, we could move flags: for_collections, for_users, for_all to the configuration of all tag processors?


@contextlib.contextmanager
def track_key_status(key: str, statuses: Statuses) -> Generator[None, None, None]:
    try:

        yield

        statuses.set(key, KeyStatus.works)

    except errors.AuthError:
        statuses.set(key, KeyStatus.broken)
        raise

    except errors.QuotaError:
        statuses.set(key, KeyStatus.quota)
        raise

    except Exception:
        statuses.set(key, KeyStatus.unknown)
        raise


# TODO: add to the documentation note about quotas of Gemini API (especially free tier)
# TODO: tests
class GoogleInterface(ProviderInterface):
    provider = LLMProvider.google

    def estimate_tokens(self, config: LLMConfiguration, text: str) -> int:
        # There are multiple ways to count tokens for Gemini:
        # 1. Use vertextai lib to count tokens locally.
        #    For now, it is too big a dependency for the project.
        #    Also, it was difficult to integrate official Google Libs.
        # 2. Use Google REST API to calculate tokens remotely.
        #    Looks like too much overhead.
        # 3. Estimate upper boundaries with a heuristic.
        #    Because the context windows of Gemini models are big
        #    this approach looks ok for start.

        # Coefficient was chosen according to ChatGPT's recommendations :-)
        return int(len(text) * 1.8)

    async def chat_request(  # type: ignore
        self, config: LLMConfiguration, api_key: str, request: GoogleChatRequest
    ) -> GoogleChatResponse:

        client = Client(api_key=api_key)

        generation_config = GenerationConfig(
            max_output_tokens=config.max_return_tokens,
            temperature=float(config.temperature),
            top_p=float(config.top_p),
            top_k=None,
        )

        try:
            with track_key_status(api_key, self.api_keys_statuses):
                answer = await client.generate_content(model=config.model, request=request, config=generation_config)

        except Exception as e:
            # temporary track all errors here till we do not implement good enough processing of them
            logger.exception("google_api_error")
            raise llmsf_errors.TemporaryError(message=str(e)) from e

        logger.info("google_response")

        return answer

    def prepare_requests(self, config: LLMConfiguration, text: str) -> Sequence[GoogleChatRequest]:  # type: ignore
        parts = llmsf_domain.split_text_according_to_tokens(llm=self, llm_config=config, text=text)

        requests = []

        for part in parts:
            request = GoogleChatRequest(
                system=ChatMessage(text=config.system), messages=[ChatMessage(role="user", text=part)]
            )

            requests.append(request)

        return requests

    async def check_api_key(self, config: LLMConfiguration, api_key: str) -> KeyStatus:
        client = Client(api_key=api_key)

        try:
            with track_key_status(api_key, self.api_keys_statuses):
                await client.list_models()
        except errors.ClientError:
            pass

        return self.api_keys_statuses.get(api_key)


provider = GoogleInterface()
