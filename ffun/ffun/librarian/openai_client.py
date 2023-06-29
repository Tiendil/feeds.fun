import asyncio
import functools
import json
import math

import async_lru
import openai
import tiktoken
import typer
from ffun.core import logging

from . import errors

logger = logging.get_module_logger()

cli = typer.Typer()


# TODO: we need to use multiple api keys
#       it looks like python client supports it as undocumented feature
#       and there are some tasks/PRs in openapi repo to support it right
def init(api_key: str):
    openai.api_key = api_key


@async_lru.alru_cache()
async def get_encoding(model):
    return tiktoken.encoding_for_model(model)


async def prepare_requests(system,  # pylint: disable=R0914
                           text,
                           model,
                           function,
                           total_tokens,
                           max_return_tokens):
    # high estimation on base of
    # https://github.com/openai/openai-cookbook/blob/main/examples/How_to_count_tokens_with_tiktoken.ipynb
    logger.info('prepare_requests')

    additional_tokens_per_message = 10

    encoding = await get_encoding(model)

    system_tokens = (additional_tokens_per_message +
                     len(encoding.encode('system')) +
                     len(encoding.encode(system)))

    text_tokens = (additional_tokens_per_message +
                   len(encoding.encode('user')) +
                   len(encoding.encode(text)))

    # rough estimation, because we don't know how exactly openai counts tokens for functions
    if function:
        function_tokens = (additional_tokens_per_message +
                           len(encoding.encode('function')) +
                           len(encoding.encode(json.dumps(function))))
    else:
        function_tokens = 0

    tokens_per_chunk = (total_tokens -
                        system_tokens -
                        max_return_tokens -
                        function_tokens -
                        additional_tokens_per_message)

    if text_tokens <= tokens_per_chunk:
        logger.info('single_chunk_text')
        return [[{'role': 'system', 'content': system},
                 {'role': 'user', 'content': text}]]

    logger.info('multiple_chunks_text', text_tokens=text_tokens, tokens_per_chunk=tokens_per_chunk)

    messages = []

    # TODO: should we split text on chunks with intersections?
    # TODO: what to do with the last small chunks?
    expected_chunks_number = text_tokens // tokens_per_chunk + 1

    expected_chunk_size = int(math.floor(len(text) / expected_chunks_number))

    logger.info('expected_chunks',
                expected_chunks_number=expected_chunks_number,
                expected_chunk_size=expected_chunk_size)

    offset = 0
    current_chunk_size = expected_chunk_size

    # expected_chunk_size is not accurate,
    # because tokens have different length in charactets
    # => number of characters to send is depends on type of part of the text,
    #    where they were taken from
    while offset < len(text):
        expected_chunk = text[offset:offset + current_chunk_size]

        expected_text_tokens = additional_tokens_per_message + len(encoding.encode(expected_chunk))

        if expected_text_tokens > tokens_per_chunk:
            current_chunk_size = math.ceil(current_chunk_size * 0.95)
            continue

        messages.append([{'role': 'system', 'content': system},
                         {'role': 'user', 'content': expected_chunk}])

        offset += current_chunk_size
        current_chunk_size = expected_chunk_size

    return messages


async def request(model,  # noqa
                  messages,
                  function,
                  max_tokens,
                  temperature,
                  top_p,
                  presence_penalty,
                  frequency_penalty):
    logger.info('request_openai')
    try:
        answer = await openai.ChatCompletion.acreate(model=model,
                                                     temperature=temperature,
                                                     max_tokens=max_tokens,
                                                     top_p=top_p,
                                                     presence_penalty=presence_penalty,
                                                     frequency_penalty=frequency_penalty,
                                                     messages=messages,
                                                     functions=[function],
                                                     function_call={'name': function['name']},)
    # https://platform.openai.com/docs/guides/error-codes/api-errors
    except openai.error.RateLimitError as e:
        logger.warning('openai_rate_limit', message=str(e))
        raise errors.SkipAndContinueLater(message=str(e)) from e
    except openai.error.APIError as e:
        logger.error('openai_api_error', message=str(e))
        raise errors.SkipAndContinueLater(message=str(e)) from e

    logger.info('openai_response')

    if function:
        return answer['choices'][0]['message']['function_call']['arguments']

    return answer['choices'][0]['message']['content']


async def multiple_requests(model,  # noqa
                            messages,
                            function,
                            max_return_tokens,
                            temperature=1,
                            top_p=0,
                            presence_penalty=1,
                            frequency_penalty=0):

    # TODO: rewrite to gather
    results = []

    for i, request_messages in enumerate(messages):
        logger.info('request', number=i, total=len(messages))
        result = await request(model=model,
                               messages=request_messages,
                               function=function,
                               max_tokens=max_return_tokens,
                               temperature=temperature,
                               top_p=top_p,
                               presence_penalty=presence_penalty,
                               frequency_penalty=frequency_penalty)

        results.append(result)

    return results
