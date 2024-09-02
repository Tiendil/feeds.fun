
from ffun.llms_framework import errors


# TODO: test
def split_text(text: str, parts: int, intersection: int) -> list[str]:
    if parts < 1:
        raise errors.TextPartsMustBePositive()

    if parts == 1:
        return [text]

    part_size = len(text) // parts + intersection // 2

    parts = []

    index = 0

    while index < len(text):
        part = text[index : index + part_size]

        parts.append(part)

        index += part_size - intersection

    return parts
