import httpx

from ffun.google import errors
from ffun.google.settings import settings
from ffun.google.entities import GoogleChatRequest, GoogleChatResponse, GenerationConfig
from ffun.llms_framework.entities import LLMConfiguration



_safety_categories = ['HARM_CATEGORY_HATE_SPEECH',
                      'HARM_CATEGORY_SEXUALLY_EXPLICIT',
                      'HARM_CATEGORY_DANGEROUS_CONTENT',
                      'HARM_CATEGORY_HARASSMENT']


class Client:
    __slots__ = ('_api_key', 'entry_point', 'model')

    def __init__(self, api_key: str, entry_point: str = settings.gemini_api_entry_point) -> None:
        self._api_key = api_key
        self.entry_point = entry_point

    async def generate_content(self,
                               model: str,
                               config: GenerationConfig,
                               request: GoogleChatRequest,
                               timeout: float = settings.gemini_api_timeout) -> str:

        headers = {'Content-Type': 'application/json'}

        url = f'{self.entry_point}/models/{model}:generateContent?key={self._api_key}'

        request = {
            'systemInstruction': request.system.to_api(),
            'contents': [message.to_api() for message in request.messages],
            'generationConfig': config.to_api(),
            'safetySettings': [{'category': category,
                                'threshold': 'BLOCK_NONE'} for category in _safety_categories],
        }

        # TODO: process errors
        async with httpx.AsyncClient(headers=headers, timeout=timeout) as client:
            response = await client.post(url, json=request)

        if response.status_code == 429:
            raise errors.QuotaError(message=response.content, status_code=response.status_code)

        if response.status_code in (401, 403):
            raise errors.AuthError(message=response.content, status_code=response.status_code)

        if response.status_code != 200:
            raise errors.UnknownError(message=response.content, status_code=response.status_code)

        response_data = response.json()

        return GoogleChatResponse(
            content=response_data['candidates'][0]['content']['parts'][0]['text'],
            prompt_tokens=response_data['usageMetadata']['promptTokenCount'],
            completion_tokens=response_data['usageMetadata']['candidatesTokenCount'],
            total_tokens=response_data['usageMetadata']['totalTokenCount'],
        )
