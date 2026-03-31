import pytest

from ffun.domain.entities import TagUid
from ffun.ontology.entities import RawTag
from ffun.tags import converters, utils
from ffun.tags.entities import NormalizationMode, TagCategory, TagInNormalization
from ffun.tags.normalizers import part_replacer

normalizer = part_replacer.Normalizer(
    replacements={
        "start-up": "startup",
        "set-up": "setup",
        "em": "them",
        "старт-ап": "стартап",
        "веб-сайт": "вебсайт",
    }
)


class TestNormalizer:
    @pytest.mark.parametrize(
        "unicode, input_uid, expected_continue, expected_new_uids",
        [
            (False, "", False, []),
            (False, "nohtingtodo", True, []),
            (False, "nohting-to-do", True, []),
            (False, "set-up-for-success", False, ["setup-for-success"]),
            (False, "best-start-up-ever", False, ["best-startup-ever"]),
            (False, "how-to-start-up", False, ["how-to-startup"]),
            (False, "let-set-up-for-start-up", False, ["let-setup-for-start-up", "let-set-up-for-startup"]),
            (False, "let-start-up-start-up", False, ["let-startup-startup"]),
            (False, "let-start-up-or-not-start-up", False, ["let-startup-or-not-startup"]),
            (False, "let-em-go", False, ["let-them-go"]),
            (True, "café-start-up-guide", False, ["café-startup-guide"]),
            (True, "let-em-идти", False, ["let-them-идти"]),
            (True, "данные-set-up-доклад", False, ["данные-setup-доклад"]),
            (True, "привет-start-up-мир", False, ["привет-startup-мир"]),
            (True, "привет-старт-ап-мир", False, ["привет-стартап-мир"]),
            (True, "мой-веб-сайт", False, ["мой-вебсайт"]),
        ],
    )
    @pytest.mark.asyncio
    async def test(
        self, unicode: bool, input_uid: TagUid, expected_continue: bool, expected_new_uids: list[str]
    ) -> None:
        assert converters.normalize(input_uid, allow_unicode=unicode) == input_uid
        assert all(converters.normalize(new_uid, allow_unicode=unicode) == new_uid for new_uid in expected_new_uids)

        categories = {TagCategory.test_preserve} if unicode else {TagCategory.test_raw}
        mode = NormalizationMode.preserve if unicode else NormalizationMode.raw

        input_tag = TagInNormalization(
            uid=input_uid,
            parts=utils.uid_to_parts(input_uid),
            link="http://example.com/tag",
            categories=categories,
            mode=mode,
        )

        expected_new_tags = [
            RawTag(
                raw_uid=new_uid,
                link=input_tag.link,
                categories=input_tag.categories,
            )
            for new_uid in expected_new_uids
        ]

        can_continue, new_tags = await normalizer.normalize(input_tag)

        new_tags.sort(key=lambda t: t.raw_uid)
        expected_new_tags.sort(key=lambda t: t.raw_uid)

        assert can_continue == expected_continue
        assert new_tags == expected_new_tags
