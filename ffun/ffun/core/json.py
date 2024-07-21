import json
from typing import Any

from ffun.core import logging

logger = logging.get_module_logger()


def format(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, check_circular=False, allow_nan=False, indent=None)


def parse(data: str) -> Any:
    return json.loads(data)


def finish_json(text: str, empty_value: str = '""') -> str:  # pylint: disable=too-many-branches # noqa: C901, CCR001
    stack = []

    text = text.strip()

    if text[-1] == ",":
        text = text[:-1]

    if text[-1] == ":":
        text += empty_value

    for c in text:
        if c == "{":
            stack.append(c)
            continue

        if c == "}":
            if stack[-1] == "{":
                stack.pop()
                continue

            raise NotImplementedError('For each "}" we expect "{"')

        if c == "[":
            stack.append(c)
            continue

        if c == "]":
            if stack[-1] == "[":
                stack.pop()
                continue

            raise NotImplementedError('For each "]" we expect "["')

        if c == '"':
            if stack[-1] == '"':
                stack.pop()
                continue

            stack.append(c)
            continue

    # fix

    while stack:
        c = stack.pop()

        if c == "{":
            text += "}"
            continue

        if c == "[":
            text += "]"
            continue

        if c == '"':
            text += '"'

            if stack[-1] == "{":
                text += f": {empty_value}"
                continue

            continue

    return text


def loads_with_fix(text: str) -> dict[str, Any]:
    try:
        return json.loads(finish_json(text))  # type: ignore
    except json.JSONDecodeError:
        return json.loads(finish_json(text))  # type: ignore


# TODO: remove if it will not be used anywhere
def extract_tags_from_random_json(data: Any) -> set[str]:
    if not data:
        # no tags if [], {}, ''
        return set()

    if isinstance(data, list):
        return set.union(*(extract_tags_from_random_json(item) for item in data))

    if isinstance(data, dict):
        return set.union(
            *(extract_tags_from_random_json(key) | extract_tags_from_random_json(value) for key, value in data.items())
        )

    if isinstance(data, str):
        return {data}

    return set()


def extract_tags_from_invalid_json(text: str) -> set[str]:
    logger.warning("try_to_extract_tags_from_an_invalid_ json", broken_source=text)

    # search all strings, believing that
    parts = text.split('"')

    tags: set[str] = set()

    is_tag = False

    while parts:
        value = parts.pop(0)

        if is_tag:
            tags.add(value)

        is_tag = not is_tag

    logger.info("tags_extracted", tags=tags)

    return tags
