import asyncio
import functools
import json
import logging
import math

import async_lru
import openai
import tiktoken
import typer
from slugify import slugify

from .settings import settings

logger = logging.getLogger(__name__)

cli = typer.Typer()


openai.api_key = settings.openai.api_key


@async_lru.alru_cache()
async def get_encoding(model):
    return tiktoken.encoding_for_model(model)


async def prepare_requests(system, text, model, total_tokens, max_return_tokens):
    # high estimation on base of
    # https://github.com/openai/openai-cookbook/blob/main/examples/How_to_count_tokens_with_tiktoken.ipynb
    additional_tokens_per_message = 10

    encoding = await get_encoding(model)

    system_tokens = (additional_tokens_per_message +
                     len(encoding.encode('system')) +
                     len(encoding.encode(system)))

    text_tokens = (additional_tokens_per_message +
                   len(encoding.encode('user')) +
                   len(encoding.encode(text)))

    tokens_per_chunk = total_tokens - system_tokens - max_return_tokens - additional_tokens_per_message

    if text_tokens <= tokens_per_chunk:
        return [[{'role': 'system', 'content': system},
                 {'role': 'user', 'content': text}]]

    messages = []

    # TODO: should we split text on chunks with intersections?
    # TODO: what to do with the last small chunks?
    expected_chunks_number = text_tokens // tokens_per_chunk + 1

    expected_chunk_size = int(math.floor(len(text) / expected_chunks_number))

    for i in range(expected_chunks_number):
        start = i * expected_chunk_size
        end = (i + 1) * expected_chunk_size

        messages.append([{'role': 'system', 'content': system},
                         {'role': 'user', 'content': text[start:end]}])

    return messages


async def request(model,  # noqa
                  messages,
                  max_tokens,
                  temperature,
                  top_p,
                  presence_penalty,
                  frequency_penalty):
    answer = await openai.ChatCompletion.acreate(model=model,
                                                 temperature=temperature,
                                                 max_tokens=max_tokens,
                                                 top_p=top_p,
                                                 presence_penalty=presence_penalty,
                                                 frequency_penalty=frequency_penalty,
                                                 messages=messages)

    content = answer['choices'][0]['message']['content']

    return content


async def multiple_requests(model,  # noqa
                            messages,
                            max_return_tokens,
                            temperature=0,
                            top_p=0,
                            presence_penalty=0,
                            frequency_penalty=0):

    # TODO: rewrite to gather
    results = []

    for request_messages in messages:
        result = await request(model=model,
                               messages=request_messages,
                               max_tokens=max_return_tokens,
                               temperature=temperature,
                               top_p=top_p,
                               presence_penalty=presence_penalty,
                               frequency_penalty=frequency_penalty)

        results.append(result)

    return results
