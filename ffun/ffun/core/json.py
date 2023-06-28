import json


def finish_json(text: str, empty_value: str|None = '""') -> str:  # pylint: disable=too-many-branches # noqa: C901, CCR001
    stack = []

    text = text.strip()

    if text[-1] == ',':
        text += empty_value

    if text[-1] == ':':
        text += empty_value

    for c in text:
        if c == '{':
            stack.append(c)
            continue

        if c == '}':
            if stack[-1] == '{':
                stack.pop()
                continue

            raise NotImplementedError()

        if c == '[':
            stack.append(c)
            continue

        if c == ']':
            if stack[-1] == '[':
                stack.pop()
                continue

            raise NotImplementedError()

        if c == '"':
            if stack[-1] == '"':
                stack.pop()
                continue

            stack.append(c)
            continue

    pairs = {'{': '}',
             '[': ']',
             '"': '"'}

    for c in reversed(stack):
        text += pairs[c]

    return text


def loads_with_fix(text: str):
    try:
        print('------')
        print(text)
        print('------')
        return json.loads(finish_json(text))
    except json.JSONDecodeError:
        return json.loads(finish_json(text))
