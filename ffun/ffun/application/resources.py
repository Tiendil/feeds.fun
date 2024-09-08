import enum


class Resource(int, enum.Enum):
    openai_tokens = 1  # TODO: comment
    tokens_cost = 2
