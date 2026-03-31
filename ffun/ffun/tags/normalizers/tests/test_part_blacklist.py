import pytest

from ffun.domain.entities import TagUid
from ffun.ontology.entities import RawTag
from ffun.tags import converters, utils
from ffun.tags.entities import NormalizationMode, TagCategory, TagInNormalization
from ffun.tags.normalizers import part_blacklist

normalizer = part_blacklist.Normalizer(blacklist={"a", "the", "и", "очень"})


class TestNormalizer:
    @pytest.mark.parametrize(
        "unicode, input_uid, expected_continue, expected_new_uids",
        [
            (False, "", False, []),
            (False, "a-the", False, []),
            (False, "no-removal", True, []),
            (False, "noremoval-at-all", True, []),
            (False, "the-best-startup", False, ["best-startup"]),
            (False, "about-the-best", False, ["about-best"]),
            (False, "about-best-the", False, ["about-best"]),
            (False, "a-or-the", False, ["or"]),
            (False, "a-the-best-of-the-best", False, ["best-of-best"]),
            (False, "athe-best", True, []),
            (False, "thea-best", True, []),
            (False, "best-thea", True, []),
            (False, "best-athe", True, []),
            (False, "know-thea-best", True, []),
            (False, "know-athe-best", True, []),
            (False, "the-the-the", False, []),
            (False, "a-a-a", False, []),
            (False, "the-a-the-a", False, []),
            (False, "a-the-a-the", False, []),
            (False, "the-a-the-a-the", False, []),
            (False, "best-the-a-the-a-the", False, ["best"]),
            (False, "math-the-a-the-a-physics", False, ["math-physics"]),
            (True, "данные-и-аналитика", False, ["данные-аналитика"]),
            (True, "résumé-и-портфолио", False, ["résumé-портфолио"]),
            (True, "очень-café-уютно", False, ["café-уютно"]),
            (True, "café-и-bistro", False, ["café-bistro"]),
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

        assert can_continue == expected_continue
        assert new_tags == expected_new_tags
