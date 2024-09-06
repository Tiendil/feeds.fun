import asyncio
import math

from ffun.library.entities import Entry
from ffun.llms_framework import errors
from ffun.llms_framework.entities import APIKeyUsage, ChatRequest, ChatResponse, LLMConfiguration, SelectKeyContext
from ffun.llms_framework.keys_rotator import choose_api_key, use_api_key
from ffun.llms_framework.provider_interface import ProviderInterface


def split_text(text: str, parts: int, intersection: int) -> list[str]:
    if parts < 1:
        raise errors.TextPartsMustBePositive()

    if intersection < 0:
        raise errors.TextIntersectionMustBePositiveOrZero()

    if not text:
        raise errors.TextIsEmpty()

    if parts == 1:
        return [text]

    base_part_size = int(math.ceil(len(text) / parts))

    if base_part_size * parts - len(text) >= base_part_size:
        raise errors.TextIsTooShort()

    text_parts: list[str] = []

    index = 0

    while index < len(text):
        left_border = max(0, index - intersection)
        right_border = min(len(text), index + base_part_size + intersection)

        part = text[left_border:right_border]

        text_parts.append(part)

        index += base_part_size

    return text_parts


def split_text_according_to_tokens(llm: ProviderInterface, llm_config: LLMConfiguration, text: str) -> list[str]:
    parts_number = 0

    model = llm.get_model(llm_config)

    while True:
        parts_number += 1

        parts = split_text(text, parts=parts_number, intersection=llm_config.text_parts_intersection)

        parts_tokens = [llm.estimate_tokens(llm_config, text=part) for part in parts]

        if any(tokens + llm_config.max_return_tokens >= model.max_context_size for tokens in parts_tokens):
            continue

        if sum(tokens + llm_config.max_return_tokens for tokens in parts_tokens) > model.max_tokens_per_entry:
            raise errors.TooManyTokensForEntry()

        return parts


async def search_for_api_key(
    llm: ProviderInterface,
    llm_config: LLMConfiguration,
    entry: Entry,
    requests: list[ChatRequest],
    # TODO: separate types for collection & general keys
    collections_api_key: str | None,
    general_api_key: str | None,
) -> APIKeyUsage | None:
    # TODO: here may be problems with too big context window for gemini
    #       (we'll reserve too much tokens), see ModelInfo.max_tokens_per_entry as a potential solution
    reserved_tokens = len(requests) * llm.get_model(llm_config).max_context_size

    select_key_context = SelectKeyContext(
        llm_config=llm_config,
        feed_id=entry.feed_id,
        entry_age=entry.age,
        reserved_tokens=reserved_tokens,
        collections_api_key=collections_api_key,
        general_api_key=general_api_key,
    )

    return await choose_api_key(llm, select_key_context)


async def call_llm(
    llm: ProviderInterface, llm_config: LLMConfiguration, api_key_usage: APIKeyUsage, requests: list[ChatRequest]
) -> list[ChatResponse]:
    async with use_api_key(api_key_usage):
        tasks = [llm.chat_request(llm_config, api_key_usage.api_key, request) for request in requests]

        responses = await asyncio.gather(*tasks)

        api_key_usage.used_tokens = sum(response.spent_tokens() for response in responses)

    return responses
