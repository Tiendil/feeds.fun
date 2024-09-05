
import pytest

from ffun.llms_framework import errors
from ffun.llms_framework.domain import split_text


class TestSplitText:

    @pytest.mark.parametrize("parts_number", [-100, -1, 0])
    def test_wrong_parts_number(self, parts_number: int) -> None:
        with pytest.raises(errors.TextPartsMustBePositive):
            split_text("some-text", parts=parts_number, intersection=0)

    @pytest.mark.parametrize("intersection", [-100, -1])
    def test_intersection_size(self, intersection: int) -> None:
        with pytest.raises(errors.TextIntersectionMustBePositiveOrZero):
            split_text("some-text", parts=1, intersection=intersection)

    def test_text_is_empty(self) -> None:
        with pytest.raises(errors.TextIsEmpty):
            split_text("", parts=1, intersection=0)

    def test_text_is_too_short(self) -> None:
        with pytest.raises(errors.TextIsTooShort):
            split_text("short", parts=len("short") + 1, intersection=0)

        with pytest.raises(errors.TextIsTooShort):
            split_text("some-text", parts=4, intersection=0)

    @pytest.mark.parametrize("text",
                             ['small-text', 'long-long-text ' * 10**6],
                             ids=['small', 'big'])
    def test_single_part(self, text: str) -> None:
        for intersection in [0, 1, 100, 1000, 10000]:
            assert split_text(text, parts=1, intersection=intersection) == [text]

    @pytest.mark.parametrize("text, parts, intersection, expected",
                             [('some-text', 1, 0, ['some-text']),
                              ('some-text', 2, 0, ['some-', 'text']),
                              ('some-text', 3, 0, ['som', 'e-t', 'ext']),

                              ('some-text', 1, 1, ['some-text']),
                              ('some-text', 2, 1, ['some-t', '-text']),
                              ('some-text', 3, 1, ['some', 'me-te', 'text']),

                              ('some-text', 1, 2, ['some-text']),
                              ('some-text', 2, 2, ['some-te', 'e-text']),
                              ('some-text', 3, 2, ['some-', 'ome-tex', '-text']),

                              ('some-text', 1, 3, ['some-text']),
                              ('some-text', 2, 3, ['some-tex', 'me-text']),
                              ('some-text', 3, 3, ['some-t', 'some-text', 'e-text']),
                              ])
    def test_split(self, text: str, parts: int, intersection: int, expected: list[str]) -> None:
        assert split_text(text, parts=parts, intersection=intersection) == expected
