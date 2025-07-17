import contextlib
from typing import Any, Generator

import httpx

from ffun.core import logging
from ffun.google import errors
from ffun.google.entities import GenerationConfig, GoogleChatRequest, GoogleChatResponse
from ffun.google.settings import settings

logger = logging.get_module_logger()

_safety_categories = [
    "HARM_CATEGORY_HATE_SPEECH",
    "HARM_CATEGORY_SEXUALLY_EXPLICIT",
    "HARM_CATEGORY_DANGEROUS_CONTENT",
    "HARM_CATEGORY_HARASSMENT",
]


class Client:
    __slots__ = ("_api_key", "entry_point", "model")

    def __init__(self, api_key: str, entry_point: str = settings.gemini_api_entry_point) -> None:
        self._api_key = api_key
        self.entry_point = entry_point

    @contextlib.contextmanager
    def _handle_network_errors(self) -> Generator[None, None, None]:
        try:
            yield
        except Exception as e:
            raise errors.UnknownError(message=str(e)) from e

    def _handle_response_status_errors(self, response: httpx.Response) -> None:
        if response.status_code == 429:
            raise errors.QuotaError(message=response.content, status_code=response.status_code)

        if response.status_code in (401, 403):
            raise errors.AuthError(message=response.content, status_code=response.status_code)

        if response.status_code != 200:
            raise errors.UnknownError(message=response.content, status_code=response.status_code)

    # See https://ai.google.dev/api/generate-content#FinishReason
    def _handle_finish_reason(self, finish_reason: str) -> None:
        match finish_reason:
            case "FINISH_REASON_UNSPECIFIED" | "STOP" | "MAX_TOKENS" | "OTHER":
                pass
            case "SAFETY" | "RECITATION" | "LANGUAGE" | "BLOCKLIST" | "SPII" | "IMAGE_SAFETY":
                # we may want to stop processing the response here
                # let's wait it there will be any issues with just passing it
                pass
            case "PROHIBITED_CONTENT":
                raise errors.ProhibitedContentError()
            case "MALFORMED_FUNCTION_CALL":
                raise errors.MalformedFunctionCallError()
            case reason:
                raise errors.UnknownFinishReasonError(reason=reason)

    # See https://ai.google.dev/api/generate-content#PromptFeedback
    def _handle_prompt_feedback(self, prompt_feedback: dict[str, Any] | None) -> None:
        if prompt_feedback is None:
            return

        if "blockReason" not in prompt_feedback:
            return

        raise errors.PromptBlocked(reason=prompt_feedback["blockReason"])

    async def generate_content(
        self,
        model: str,
        config: GenerationConfig,
        request: GoogleChatRequest,
        timeout: float = settings.gemini_api_timeout,
    ) -> GoogleChatResponse:

        headers = {"Content-Type": "application/json"}

        url = f"{self.entry_point}/models/{model}:generateContent?key={self._api_key}"

        http_request = {
            "systemInstruction": request.system.to_api(),
            "contents": [message.to_api() for message in request.messages],
            "generationConfig": config.to_api(),
            "safetySettings": [{"category": category, "threshold": "BLOCK_NONE"} for category in _safety_categories],
        }

        with self._handle_network_errors():
            async with httpx.AsyncClient(headers=headers, timeout=timeout) as client:
                response = await client.post(url, json=http_request)

        self._handle_response_status_errors(response)

        response_data = response.json()

        # There is cases where no candidates are returned
        # => Check prompt feedback before processing candidates
        # See https://ai.google.dev/api/generate-content#generatecontentresponse
        # Also, it looks like `promptFeedback` is optional => we use `get` instead of `[]`
        self._handle_prompt_feedback(response_data.get("promptFeedback"))

        candidate = response_data["candidates"][0]

        self._handle_finish_reason(candidate["finishReason"])

        return GoogleChatResponse(
            content=candidate["content"]["parts"][0]["text"],
            prompt_tokens=response_data["usageMetadata"]["promptTokenCount"],
            completion_tokens=response_data["usageMetadata"]["candidatesTokenCount"],
            total_tokens=response_data["usageMetadata"]["totalTokenCount"],
        )

    async def list_models(self, timeout: float = settings.gemini_api_timeout) -> list[dict[str, Any]]:
        headers = {"Content-Type": "application/json"}

        url = f"{self.entry_point}/models?key={self._api_key}"

        with self._handle_network_errors():
            async with httpx.AsyncClient(headers=headers, timeout=timeout) as client:
                response = await client.get(url)

        self._handle_response_status_errors(response)

        # TODO: introduce entity class for models
        return response.json()["models"]  # type: ignore
