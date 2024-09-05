import httpx

from ffun.google.settings import settings
from ffun.google.entities import GoogleChatRequest, GoogleChatResponse
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

    # TODO: maybe introduce separate classes for request/response
    # TODO: system message is duplicated in config & request
    async def generate_content(self,
                               config: LLMConfiguration,
                               request: GoogleChatRequest,
                               timeout: float = settings.gemini_api_timeout) -> str:

        headers = {'Content-Type': 'application/json'}

        url = f'{self.entry_point}/models/{config.model}:generateContent?key={self._api_key}'

        request = {
            'systemInstruction': {'parts': [{'text': config.system}]},
            'contents': [{'parts': [{'text': request.user_message}]}],  # TODO: better object?
            'generationConfig': {
                'candidateCount': 1,
                'stopSequences': [],
                'responseMimeType': 'text/plain',
                'responseSchema': None,
                'maxOutputTokens': config.max_return_tokens,
                'temperature': float(config.temperature),
                'topP': float(config.top_p),
                'topK': None
            },
            'safetySettings': [{'category': category,
                                'threshold': 'BLOCK_NONE'} for category in _safety_categories],
        }

        # TODO: process errors
        async with httpx.AsyncClient(headers=headers, timeout=timeout) as client:
            response = await client.post(url, json=request)

        print()
        print(response.json())
        print()

        # TODO: add correct exception
        if response.status_code != 200:
            raise NotImplementedError(f'Error: {response.status_code}')

        response_data = response.json()

        return GoogleChatResponse(
            content=response_data['candidates'][0]['content']['parts'][0]['text'],
            prompt_tokens=response_data['usageMetadata']['promptTokenCount'],
            completion_tokens=response_data['usageMetadata']['candidatesTokenCount'],
            total_tokens=response_data['usageMetadata']['totalTokenCount'],
        )


# curl https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key=$GOOGLE_API_KEY \
#     -H 'Content-Type: application/json' \
#     -X POST \
#     -d '{
#         "contents": [{
#             "parts":[
#                 {"text": "Write a story about a magic backpack."}
#             ]
#         }],
#         "safetySettings": [
#             {
#                 "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
#                 "threshold": "BLOCK_ONLY_HIGH"
#             }
#         ],
#         "generationConfig": {
#             "stopSequences": [
#                 "Title"
#             ],
#             "temperature": 1.0,
#             "maxOutputTokens": 800,
#             "topP": 0.8,
#             "topK": 10
#         }
#     }'  2> /dev/null | grep "text"
