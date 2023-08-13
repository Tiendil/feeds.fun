import pytest

from ffun.tags.converters import _decode_special_characters, _encode_special_characters, normalize


class TestEncodeSpecialCharacters:
    @pytest.mark.parametrize(
        "tag, expected",
        [
            ("abc", "abc"),
            ("abc def", "abc def"),
            ("c++", "c-plus--plus-"),
            ("c#", "c-sharp-"),
            ("www.example.com", "www-dot-example-dot-com"),
        ],
    )
    def test(self, tag: str, expected: str) -> None:
        assert _encode_special_characters(tag) == expected


class TestNormalize:
    @pytest.mark.parametrize(
        "tag, expected",
        [
            ("abc", "abc"),
            ("abc def", "abc-def"),
            ("c++", "c-plus-plus"),
            ("c#", "c-sharp"),
            ("www.example.com", "www-dot-example-dot-com"),
        ],
    )
    def test(self, tag: str, expected: str) -> None:
        assert normalize(tag) == expected


class TestDecodeSpecialCharacters:
    @pytest.mark.parametrize(
        "tag, expected",
        [
            ("abc", "abc"),
            ("abc-def", "abc-def"),
            ("c-plus-plus", "c++"),
            ("c-sharp", "c#"),
            ("www-dot-example-dot-com", "www.example.com"),
        ],
    )
    def test(self, tag: str, expected: str) -> None:
        assert _decode_special_characters(tag) == expected
