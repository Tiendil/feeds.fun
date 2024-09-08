from typing import Any

import pydantic

from ffun.core.entities import BaseEntity
from ffun.llms_framework.provider_interface import ChatRequest, ChatResponse


class ChatMessage(BaseEntity):
    role: str | None = None
    text: str

    def to_api(self) -> dict[str, Any]:
        data = {"parts": [{"text": self.text}]}

        if self.role is not None:
            data["role"] = self.role  # type: ignore

        return data


class GoogleChatRequest(ChatRequest):
    system: ChatMessage
    messages: list[ChatMessage]


class GoogleChatResponse(ChatResponse):
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


class GenerationConfig(BaseEntity):
    candidates_count: int = 1
    stop_sequences: tuple[str, ...] = pydantic.Field(default_factory=tuple)
    response_mime_type: str = "text/plain"
    response_schema: dict[str, Any] | None = None
    max_output_tokens: int
    temperature: float
    top_p: float
    top_k: int | None

    def to_api(self) -> dict[str, Any]:
        return {
            "candidateCount": self.candidates_count,
            "stopSequences": self.stop_sequences,
            "responseMimeType": self.response_mime_type,
            "responseSchema": self.response_schema,
            "maxOutputTokens": self.max_output_tokens,
            "temperature": self.temperature,
            "topP": self.top_p,
            "topK": self.top_k,
        }
