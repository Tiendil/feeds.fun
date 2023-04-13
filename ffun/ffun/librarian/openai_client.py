import json
import logging

import openai
import typer
from slugify import slugify

from .settings import settings

logger = logging.getLogger(__name__)

cli = typer.Typer()


openai.api_key = settings.openai.api_key

# TODO: how to reflect dates in ontology, but only dates from text, not dates of publication?
# TODO: split humand languages with programming languages
# TODO platform:youtube is it about any video on youtube, or about youtube itself? What about source:youtube?
# TODO: "topic:programming-language" vs "topic:programming-languages". GPT must generate lables only in singular form?
# TODO: author иногда определяется криво. Не как автора статьи, а как автор цитаты или автор того, на что статья ссылается.
# TODO: if we add specific tag, like "product:recident-evil-2", we should add more general tag like "product:recident-evil" too.

types = ["topic", "author", "genre", "language", "country", "city", "organization", "person", "event", "work", "product", "author", "platform", "sentiment", "audience", "purpose", "region", "source", "industry", "licence", "book", "programming_language", "framework", "library", "tool", "platform", "development_methodology", "software_architecture", "design_pattern", "algorithm", "data_structure", "file_format", "protocol", "software_license", "operating_system", "software_category", "software"]


system = f'''You will act as an expert on the classification of texts. For received HTML, you should assign labels/tags in the format `<type>:<categoty>`. For example, `topic:politics`, `author:conan_doyle`. Labels should be normalized, allowed characters for labels: `[a-z0-9_]`.

You will give answers only in strict JSON format. No free-form text allowed. No intro text allowed. No additional text is allowed. Only JSON.

Allowed types are: {types}.

No other types are allowed.

You can return an empty list if you are unsure about the labels. It is not an error.

In case of an error, you should return a JSON object with an "error" field. For example: {{"error": "some error message"}}.

Expected JSON format: {{"labels": ["label1", "label2"]}}
'''


system_experimental = '''
You are an expert on the analysis of text semantics.
For provided text, you determine a list of tags.
You always detect a related tag for each name or caption from the text.
You always provide a wide variation of tags.
You always output all possible tags, regardless of possible errors.

You determine tags of the next types:

- `author`: the person responsible for creating the text, such as the name of a journalist, writer, etc.
- `sentiment`: the overall sentiment expressed in the text, such as `positive`, `negative`, or `neutral`, etc.
- `genre`: the type of content or style, such as `news`, `fiction`, `opinion`, `essay`, `review`, `science-fiction`, etc.
- `language`: The language the text is written in, such as `english`, `spanish`, `french`, etc.
- `entity`:  any named real-world or imagined object, person, place, organization or anything else mentioned in the text. For example, `entity:google`, `entity:barack-obama`, `entity:voltron`.
- `concept`: any abstract ideas, categories, or themes related to the text but not necessarily mentioned explicitly. For example, `concept:climate-change` , `concept:artificial-intelligence`.

Output must be:

- Single tag per line.
- No free-form text allowed.
- No intro text allowed.
- No additional text is allowed.

Example:

```
concept:politics
author:conan-doyle
```
'''

gpt_3_5_experimental = '''
You are an expert on the analysis of text semantics.
For provided text, you determine a list of best tags to describe the text.
You always provide significant tags for topics.
You always provide significant tags for mentioned entities and concepts.
If a topic has a meta topic you add it too.
You add an explanation for each tag.

Output must be:

- Single tag per line.
- No free-form text allowed.
- No intro text allowed.
- No additional text is allowed.

Output example:

```
topics:
1. amazon: because the text is about amazon
...
19. lord-of-the-rings: because the text is about amazon

meta-topics:
1. corporations: because amazon is a corporation
...
15. middle-earth: because the lord-of-the-rings is about middle-earth

related-topics:

1. tolkien: because tolkien is the author of lord-of-the-rings
...
15. fantasy: because it is the genre of the lord-of-the-rings

mentions:
1. politics: because recent politics events are mentioned in the text
...
20. conan-doyle: because conan-doyle is mentioned in the text
```
'''


def normalize(label):
    if ':' not in label:
        return None

    type, category = label.split(':', 1)

    return f'{slugify(type)}:{slugify(category)}'


def is_valid_tag(label):
    if label is None:
        return False

    if ':' not in label:
        return False

    type, _ = label.split(':')

    return type in types


# TODO: can we continue chat, without restarting it?
async def get_labels_by_html(article):

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
