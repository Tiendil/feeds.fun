
from typing import Iterable


class BaseRule:
    __slots__ = ()

    def score(self, tags: set[int]) -> int:
        raise NotImplementedError()


class HasTags(BaseRule):
    __slots__ = ('_tags', '_score')

    def __init__(self, tags: Iterable[int], score: int) -> None:
        self._tags = frozenset(tags)
        self._score = score

    def score(self, tags: set[int]) -> int:
        if self._tags <= tags:
            return self._score

        return 0
