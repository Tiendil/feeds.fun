import re

RE_DOG_TAG = re.compile(r"@([\w\d-]+)")


def dog_tags_extractor(text: str) -> set[str]:
    return set(tag.lower() for tag in RE_DOG_TAG.findall(text))
