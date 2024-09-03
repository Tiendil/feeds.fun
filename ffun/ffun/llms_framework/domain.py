import asyncio

from ffun.llms_framework.provider_interface import ProviderInterface

from ffun.library.entities import Entry
from ffun.llms_framework import errors
from ffun.llms_framework.entities import APIKeyUsage, ChatRequest, ChatResponse, LLMConfiguration, SelectKeyContext
from ffun.llms_framework.keys_rotator import choose_api_key, use_api_key
from ffun.llms_framework.providers import llm_providers


# TODO: test
def split_text(text: str, parts: int, intersection: int) -> list[str]:
    if parts < 1:
        raise errors.TextPartsMustBePositive()

    if parts == 1:
        return [text]

    part_size = len(text) // parts + intersection // 2

    text_parts: list[str] = []

    index = 0

    while index < len(text):
        part = text[index : index + part_size]

        text_parts.append(part)

        index += part_size - intersection

    return text_parts


# TODO: tests
def split_text_according_to_tokens(llm: ProviderInterface, config: LLMConfiguration, text: str) -> list[str]:
    parts_number = 0

    max_context_size = llm.max_context_size_for_model(config)

    # TODO: move to common code
    while True:
        parts_number += 1

        parts = split_text(text, parts=parts_number, intersection=config.text_parts_intersection)

        parts_tokens = [llm.estimate_tokens(config,
                                            text=part)
                        for part in parts]

        if any(tokens + config.max_return_tokens >= max_context_size for tokens in parts_tokens):
            continue

        # if sum(tokens + max_return_tokens for tokens in parts_tokens) >= max_context_size:
        #     break

        return parts


# TODO: test
async def search_for_api_key(
        llm_config: LLMConfiguration,
        entry: Entry,
        requests: list[ChatRequest],
        collections_api_key: str | None,
        general_api_key: str | None
) -> APIKeyUsage:
    llm = llm_providers.get(llm_config.provider).provider

    reserved_tokens = len(requests) * llm.max_context_size_for_model(llm_config)

    select_key_context = SelectKeyContext(llm_config=llm_config,
                                          feed_id=entry.feed_id,
                                          entry_age=entry.age,
                                          reserved_tokens=reserved_tokens,
                                          collections_api_key=collections_api_key,
                                          general_api_key=general_api_key)

    return await choose_api_key(select_key_context)


# TODO: tests
async def call_llm(
    llm_config: LLMConfiguration, api_key_usage: APIKeyUsage, requests: list[ChatRequest]
) -> list[ChatResponse]:
    llm = llm_providers.get(llm_config.provider).provider

    async with use_api_key(api_key_usage):
        tasks = [llm.chat_request(llm_config, api_key_usage.api_key, request) for request in requests]

        responses = await asyncio.gather(*tasks)

        api_key_usage.used_tokens = sum(response.spent_tokens() for response in responses)

    return responses
