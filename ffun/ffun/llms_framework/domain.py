import asyncio
import math
from decimal import Decimal
from typing import Sequence

from ffun.core import logging
from ffun.domain.datetime_intervals import month_interval_start
from ffun.library import domain as l_domain
from ffun.library.entities import Entry
from ffun.llms_framework import errors
from ffun.llms_framework.entities import (
    APIKeyUsage,
    ChatRequest,
    ChatResponse,
    LLMCollectionApiKey,
    LLMConfiguration,
    LLMGeneralApiKey,
    LLMTokens,
    ModelInfo,
    SelectKeyContext,
    USDCost,
)
from ffun.llms_framework.keys_rotator import choose_user_api_key, use_api_key
from ffun.llms_framework.provider_interface import ProviderInterface

logger = logging.get_module_logger()


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


def split_text_according_to_tokens(  # noqa: CCR001
    llm: ProviderInterface,
    llm_config: LLMConfiguration,
    text: str,
    text_parts_intersection: int,
) -> list[str]:
    parts_number = 0

    model = llm.get_model(llm_config)

    while True:
        parts_number += 1

        parts = split_text(text, parts=parts_number, intersection=text_parts_intersection)

        parts_tokens = [llm.estimate_tokens(llm_config, text=part) for part in parts]

        if any(tokens + llm_config.max_return_tokens >= model.max_context_size for tokens in parts_tokens):
            continue

        return parts


def cut_text_to_max_tokens(  # noqa: CCR001
    llm: ProviderInterface,
    llm_config: LLMConfiguration,
    text: str,
    max_tokens: LLMTokens,
) -> str:

    if max_tokens <= 0:
        raise errors.MaxTokensMustBePositive()

    left_border = 0

    right_border = len(text)
    right_tokens = llm.estimate_tokens(llm_config, text=text)

    if right_tokens <= max_tokens:
        return text

    while True:
        mid_border = (left_border + right_border) // 2
        mid_tokens = llm.estimate_tokens(llm_config, text=text[:mid_border])

        if mid_tokens > max_tokens:
            right_border = mid_border
            right_tokens = mid_tokens
        else:
            left_border = mid_border

        if right_border - left_border <= 1:
            break

    return text[:left_border]


def _estimate_reserved_cost(
    llm: ProviderInterface, llm_config: LLMConfiguration, requests: Sequence[ChatRequest]
) -> USDCost:
    # TODO: here may be problems with too big context window for gemini
    #       (we'll reserve too much tokens), see ModelInfo.max_tokens_per_entry as a potential solution
    model = llm.get_model(llm_config)

    return USDCost(len(requests) * model.max_request_cost)


def general_api_key_usage(
    *,
    llm: ProviderInterface,
    llm_config: LLMConfiguration,
    api_key: LLMGeneralApiKey,
    requests: Sequence[ChatRequest],
) -> APIKeyUsage:
    reserved_cost = _estimate_reserved_cost(llm=llm, llm_config=llm_config, requests=requests)

    return APIKeyUsage(
        provider=llm.provider,
        user_id=None,
        api_key=api_key,
        reserved_cost=reserved_cost,
        used_cost=None,
        interval_started_at=month_interval_start(),
    )


def collection_api_key_usage(
    *,
    llm: ProviderInterface,
    llm_config: LLMConfiguration,
    api_key: LLMCollectionApiKey,
    requests: Sequence[ChatRequest],
) -> APIKeyUsage:
    reserved_cost = _estimate_reserved_cost(llm=llm, llm_config=llm_config, requests=requests)

    return APIKeyUsage(
        provider=llm.provider,
        user_id=None,
        api_key=api_key,
        reserved_cost=reserved_cost,
        used_cost=None,
        interval_started_at=month_interval_start(),
    )


async def search_for_user_api_key(
    llm: ProviderInterface,
    llm_config: LLMConfiguration,
    entry: Entry,
    requests: Sequence[ChatRequest],
) -> APIKeyUsage | None:
    reserved_cost = _estimate_reserved_cost(llm=llm, llm_config=llm_config, requests=requests)

    feed_ids = await l_domain.get_feeds_for_entry(entry.id)

    select_key_context = SelectKeyContext(
        llm_config=llm_config,
        feed_ids=feed_ids,
        entry_age=entry.age_for_processing,
        reserved_cost=reserved_cost,
    )

    return await choose_user_api_key(llm, select_key_context)


def _llm_call_result_cost(model: ModelInfo, result: ChatResponse | BaseException) -> USDCost:
    if isinstance(result, errors.RequestWasRejected):
        return USDCost(Decimal(0))

    if isinstance(result, BaseException):
        return model.max_request_cost

    return model.tokens_cost(input_tokens=result.input_tokens(), output_tokens=result.output_tokens())


async def call_llm(
    llm: ProviderInterface, llm_config: LLMConfiguration, api_key_usage: APIKeyUsage, requests: Sequence[ChatRequest]
) -> list[ChatResponse]:

    model = llm.get_model(llm_config)

    async with use_api_key(api_key_usage):
        tasks = [llm.chat_request(llm_config, api_key_usage.api_key, request) for request in requests]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        used_cost = USDCost(Decimal(0))

        first_request_error: BaseException | None = None  # TODO: maybe we should use ExceptionGroup there.

        for result in results:
            used_cost += _llm_call_result_cost(model, result)  # type: ignore

            if isinstance(result, BaseException):
                if first_request_error is None:
                    first_request_error = result

                continue

        api_key_usage.used_cost = used_cost

        if first_request_error is not None:
            raise first_request_error

    return results  # type: ignore
