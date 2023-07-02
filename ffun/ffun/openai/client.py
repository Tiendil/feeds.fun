import asyncio
import functools
import json
import math

import async_lru
import tiktoken
import typer
from ffun.core import logging

import openai

from . import entities, errors

logger = logging.get_module_logger()

cli = typer.Typer()


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


async def request(api_key,  # noqa
                  model,
                  messages,
                  function,
                  max_tokens,
                  temperature,
                  top_p,
                  presence_penalty,
                  frequency_penalty):
    logger.info('request_openai')

    arguments = {}

    if function is not None:
        arguments['functions'] = [function]
        arguments['function_call'] = {'name': function['name']}

    try:
        answer = await openai.ChatCompletion.acreate(api_key=api_key,
                                                     model=model,
                                                     temperature=temperature,
                                                     max_tokens=max_tokens,
                                                     top_p=top_p,
                                                     presence_penalty=presence_penalty,
                                                     frequency_penalty=frequency_penalty,
                                                     messages=messages,
                                                     **arguments)
    # https://platform.openai.com/docs/guides/error-codes/api-errors
    except openai.error.RateLimitError as e:
        logger.warning('openai_rate_limit', message=str(e))
        raise errors.TemporaryError(message=str(e)) from e
    except openai.error.ServiceUnavailableError as e:
        logger.warning('openai_service_unavailable', message=str(e))
        raise errors.TemporaryError(message=str(e)) from e
    except openai.error.APIError as e:
        logger.error('openai_api_error', message=str(e))
        raise errors.TemporaryError(message=str(e)) from e

    logger.info('openai_response')

    if function:
        content = answer['choices'][0]['message']['function_call']['arguments']
    else:
        content = answer['choices'][0]['message']['content']

    return entities.OpenAIAnswer(content=content,
                                 prompt_tokens=answer['usage']['prompt_tokens'],
                                 completion_tokens=answer['usage']['completion_tokens'],
                                 total_tokens=answer['usage']['total_tokens'])


async def multiple_requests(api_key,  # noqa
                            model,
                            messages,
                            function,
                            max_return_tokens,
                            temperature,
                            top_p,
                            presence_penalty,
                            frequency_penalty):

    # TODO: rewrite to gather
    #       also, it seems OpenAI API support sending multiple threads in a single request
    results = []

    for i, request_messages in enumerate(messages):
        logger.info('request', number=i, total=len(messages))
        result = await request(api_key=api_key,
                               model=model,
                               messages=request_messages,
                               function=function,
                               max_tokens=max_return_tokens,
                               temperature=temperature,
                               top_p=top_p,
                               presence_penalty=presence_penalty,
                               frequency_penalty=frequency_penalty)

        results.append(result)

    return results


async def check_api_key(api_key) -> entities.KeyStatus:
    try:
        # TODO: check if it is ok to use Model.list
        await openai.Model.alist(api_key=api_key)
        logger.info('correct_api_key')
    except openai.error.AuthenticationError:
        logger.info('wrong_api_key')
        return entities.KeyStatus.broken
    except Exception:
        logger.exception('unknown_error_while_checking_api_key')
        return entities.KeyStatus.unknown

    return entities.KeyStatus.works
