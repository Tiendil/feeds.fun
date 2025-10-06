import pydantic
import pytest

from ffun.scores import errors
from ffun.scores.entities import Rule
from ffun.scores.tests.helpers import rule


def replace_tags(r: Rule, mapping: dict[int, int]) -> tuple[set[int], set[int]]:
    return r.replace_tags({k: v for k, v in mapping.items()})  # type: ignore


class TestRule:

    def test_replace_tags__circular_replacement(self) -> None:
        r = rule(10, {1, 2}, {3})

        with pytest.raises(errors.CircularTagReplacement):
            replace_tags(r, {1: 2, 3: 4, 4: 1})

    def test_replace_tags__duplicated_tags_in_result(self) -> None:
        r = rule(10, {1, 2}, {3})

        with pytest.raises(errors.RuleTagsIntersection):
            replace_tags(r, {2: 3})

    def test_replace_tags__replace_tags(self) -> None:
        r = rule(10, {1, 2, 3}, {4, 5})

        new_required, new_excluded = replace_tags(r, {2: 10, 3: 11, 5: 30})

        assert new_required == {1, 10, 11}
        assert new_excluded == {4, 30}

    def test_replace_tags__merging_with_duplicates_in_tags(self) -> None:
        r = rule(10, {1, 2, 3}, {4, 5})

        new_required, new_excluded = replace_tags(r, {2: 1, 3: 11, 5: 4})

        assert new_required == {1, 11}
        assert new_excluded == {4}

    def test_replace_tags__merging_with_duplicates_in_new(self) -> None:
        r = rule(10, {1, 2, 3}, {4, 5})

        new_required, new_excluded = replace_tags(r, {2: 11, 3: 11, 5: 13, 4: 13})

        assert new_required == {1, 11}
        assert new_excluded == {13}

    def test_protection_from_duplicates(self) -> None:
        with pytest.raises(pydantic.ValidationError) as exc_info:
            rule(10, {1, 2, 3}, {3, 4, 5})

        assert "A tag cannot be both required and excluded" in str(exc_info.value)
