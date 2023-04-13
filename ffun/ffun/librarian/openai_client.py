import json
import logging

import openai
import typer
from slugify import slugify

from .settings import settings

logger = logging.getLogger(__name__)

cli = typer.Typer()


openai.api_key = settings.openai.api_key


async def prepare_requests(system, text, model, total_tokens, max_return_tokens):
    # high estimation on base of
    # https://github.com/openai/openai-cookbook/blob/main/examples/How_to_count_tokens_with_tiktoken.ipynb
    additional_tokens_per_message = 10

    ###############################
    # TODO: detect full model name
    # TODO: move out of this function
    full_model_name = model
    encoding = tiktoken.encoding_for_model(full_model_name)
    ###############################

    system_tokens = (additional_tokens_per_message +
                     len(encoding.encode('system')) +
                     len(encoding.encode(system)))

    text_tokens = (additional_tokens_per_message +
                   len(encoding.encode('user')) +
                   len(encoding.encode(text)))

    tokens_per_chunk = total_tokens - system_tokens - max_return_tokens

    if text_tokens <= tokens_per_chunk:
        yield [{'role': 'system', 'content': system},
               {'role': 'user', 'content': text}]

    # TODO: should we split text on chunks with intersections?
    # TODO: what to do with the last small chunks?
    expected_chunks_number = text_tokens // tokens_per_chunk + 1

    for i in range(expected_chunks_number):
        start = i * tokens_per_chunk
        end = (i + 1) * tokens_per_chunk

        yield [{'role': 'system', 'content': system},
               {'role': 'user', 'content': text[start:end]}]



# TODO: can we continue chat, without restarting it?
async def get_labels_by_html(text,
                             model,
                             total_tokens,
                             max_return_tokens,
                             temperature=0,
                             top_p=0,
                             presence_penalty=0,
                             frequency_penalty=0):

    n = 3000

    labels = set()

    while article:
        messages = [{"role": "system", "content": system},
                    {"role": "assistant", "content": 'html: ' + article[:n]}]

        article = article[n:]

        print('Send request to OpenAI...')

        try:
            response = await openai.ChatCompletion.acreate(model=settings.openai.model,
                                                           temperature=0,
                                                           max_tokens=1000,
                                                           messages=messages)
        except Exception:
            logger.exception('openAI request error')
            return None

        content = response['choices'][0]['message']['content']

        try:
            answer = json.loads(content)
        except json.decoder.JSONDecodeError:
            logger.exception('OpenAI returned invalid JSON: %s', content)
            continue

        try:
            new_labels = answer['labels']
        except KeyError:
            logger.exception('wrong labels format. better to improve GPT configuration')
            continue

        if not isinstance(new_labels, (list, set)):
            logger.error('wrong labels format %s. better to improve GPT configuration', new_labels)
            continue

        for l in new_labels:
            if not isinstance(l, str):
                logger.error('wrong labels format "%s". better to improve GPT configuration', l)
                continue

            labels.add(l)

    normalized_labels = {normalize(l) for l in labels}

    return {l for l in normalized_labels if is_valid_tag(l)}
