
import pytest

from ffun.librarian.text_cleaners import clear_nothing, clear_html


class TestClearNothing:

    @pytest.mark.parametrize("input_text, expected_text",
                             [('', ''),
                              ('some-text some-text', 'some-text some-text'),
                              ('some <tagged> text</tagged>', 'some <tagged> text</tagged>')])
    def test(self, input_text: str, expected_text: str) -> None:
        assert clear_nothing(input_text) == expected_text
