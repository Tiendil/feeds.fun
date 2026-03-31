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
        "tag, allow_unicode, expected",
        [
            ("abc", False, "abc"),
            ("abc def", False, "abc-def"),
            ("c++", False, "c-plus-plus"),
            ("c#", False, "c-sharp"),
            ("www.example.com", False, "www-dot-example-dot-com"),
            ("abc", True, "abc"),
            ("Café au lait", False, "cafe-au-lait"),
            ("Café au lait", True, "café-au-lait"),
            ("Привет мир", True, "привет-мир"),
            ("ＡＢＣ", True, "abc"),
            ("① ② ③", True, "1-2-3"),
            ("㍍", True, "メートル"),
            ("ﬁle name", True, "file-name"),
        ],
    )
    def test(self, tag: str, allow_unicode: bool, expected: str) -> None:
        assert normalize(tag, allow_unicode=allow_unicode) == expected

    @pytest.mark.parametrize(
        "left, right, expected",
        [
            ("Café au lait", "Cafe\u0301 au lait", "café-au-lait"),
            ("ＡＢＣ", "ABC", "abc"),
            ("Ångström", "Ångström", "ångström"),
            ("① ② ③", "1 2 3", "1-2-3"),
            ("㍍", "メートル", "メートル"),
            ("ﬁle name", "file name", "file-name"),
        ],
    )
    def test_unicode_forms_collapse_to_single_slug(self, left: str, right: str, expected: str) -> None:
        assert normalize(left, allow_unicode=True) == expected
        assert normalize(right, allow_unicode=True) == expected


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
