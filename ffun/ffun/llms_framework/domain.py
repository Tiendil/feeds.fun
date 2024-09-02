
from ffun.llms_framework.entities import LLMConfiguration
from ffun.llms_framework import errors
from ffin.llms_framework.provider_interface import ProviderInterface


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


# TODO: tests
def split_text_according_to_tokens(llm: ProviderInterface,
                                   config: LLMConfiguration,
                                   text: str) -> list[str]:
    parts_number = 0

    max_context_size = llm.max_context_size_for_model(config.model)

    # TODO: move to common code
    while True:
        parts_number += 1

        parts = split_text(text, parts=parts_number, intersection=config.text_parts_intersection)

        parts_tokens = [llm.estimate_tokens(config.model,
                                            system=config.system,
                                            text=part) for part in parts]

        if any(tokens + config.max_return_tokens >= max_context_size for tokens in parts_tokens):
            continue

        # if sum(tokens + max_return_tokens for tokens in parts_tokens) >= max_context_size:
        #     break

        return parts
