import pytest

from ffun.tags.converters import _encode_special_characters


class TestEncodeSpecialCharacters:

    @pytest.mark.parametrize('tag, expected', [('', ''),
                                               ('abc', 'abc'),
                                               ('abc def', 'abc def'),
                                               ('c++', 'c-plus--plus-'),
                                               ('c#', 'c-sharp-'),
                                               ('www.example.com', 'www-dot-example-dot-com')])
    def test(self, tag: str, expected: str) -> None:
        assert _encode_special_characters(tag) == expected
