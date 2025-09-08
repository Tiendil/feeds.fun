import pytest

from ffun.domain.entities import TagUid
from ffun.tags import errors
from ffun.tags.entities import TagUidPart
from ffun.tags.utils import dashes_for_tag_part, uid_to_parts


class TestUidToParts:

    @pytest.mark.parametrize(
        "input_uid, parts",
        [
            ("", []),
            ("nohtingtodo", ["nohtingtodo"]),
            ("nohting-to-do", ["nohting", "to", "do"]),
            ("set-up-for-success", ["set", "up", "for", "success"]),
        ],
    )
    def test(self, input_uid: TagUid, parts: list[str]) -> None:
        assert uid_to_parts(input_uid) == [TagUidPart(part) for part in parts]


class TestDashesForTagPart:

    @pytest.mark.parametrize(
        "in_text, out_text",
        [
            ("text", "-text-"),
            ("-text", "-text-"),
            ("text-", "-text-"),
            ("-text-", "-text-"),
            ("some-text", "-some-text-"),
        ],
    )
    def test(self, in_text: str, out_text: str) -> None:
        assert dashes_for_tag_part(in_text) == out_text

    def test_error_on_empty_part(self) -> None:
        with pytest.raises(errors.TagPartIsEmpty):
            dashes_for_tag_part("")
