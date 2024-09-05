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
