import json


def finish_json(text: str) -> str:
    stack = []

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
        return json.loads(finish_json(text))
    except json.JSONDecodeError:
        return json.loads(finish_json(text))
