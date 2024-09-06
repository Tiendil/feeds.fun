import contextlib
from typing import Any, Generator

import httpx

from ffun.google import errors
from ffun.google.entities import GenerationConfig, GoogleChatRequest, GoogleChatResponse
from ffun.google.settings import settings

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

    def _handle_response_errors(self, response: httpx.Response) -> None:
        if response.status_code == 429:
            raise errors.QuotaError(message=response.content, status_code=response.status_code)

        if response.status_code in (401, 403):
            raise errors.AuthError(message=response.content, status_code=response.status_code)

        if response.status_code != 200:
            raise errors.UnknownError(message=response.content, status_code=response.status_code)

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

        self._handle_response_errors(response)

        response_data = response.json()

        return GoogleChatResponse(
            content=response_data["candidates"][0]["content"]["parts"][0]["text"],
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

        self._handle_response_errors(response)

        # TODO: introduce entity class for models
        return response.json()["models"]  # type: ignore
