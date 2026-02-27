import re

RE_DOG_TAG: re.Pattern[str] = re.compile(r"@([\w\d-]+)")


def dog_tags_extractor(text: str) -> set[str]:
    results: list[str] = RE_DOG_TAG.findall(text)
    return {tag.lower() for tag in results}
