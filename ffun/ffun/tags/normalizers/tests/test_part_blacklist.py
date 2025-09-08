import pytest

from ffun.domain.entities import TagUid
from ffun.ontology.entities import NormalizationMode, RawTag
from ffun.tags import converters, utils
from ffun.tags.entities import TagCategory, TagInNormalization
from ffun.tags.normalizers import part_blacklist

normalizer = part_blacklist.Normalizer(blacklist={"a", "the"})


class TestNormalizer:
    @pytest.mark.parametrize(
        "input_uid, expected_continue, expected_new_uids",
        [
            ("", False, []),
            ("a-the", False, []),
            ("no-removal", True, []),
            ("noremoval-at-all", True, []),
            ("the-best-startup", False, ["best-startup"]),
            ("about-the-best", False, ["about-best"]),
            ("about-best-the", False, ["about-best"]),
            ("a-or-the", False, ["or"]),
            ("a-the-best-of-the-best", False, ["best-of-best"]),
            ("athe-best", True, []),
            ("thea-best", True, []),
            ("best-thea", True, []),
            ("best-athe", True, []),
            ("know-thea-best", True, []),
            ("know-athe-best", True, []),
            ("the-the-the", False, []),
            ("a-a-a", False, []),
            ("the-a-the-a", False, []),
            ("a-the-a-the", False, []),
            ("the-a-the-a-the", False, []),
            ("best-the-a-the-a-the", False, ["best"]),
            ("math-the-a-the-a-physics", False, ["math-physics"]),
        ],
    )
    @pytest.mark.asyncio
    async def test(self, input_uid: TagUid, expected_continue: bool, expected_new_uids: list[str]) -> None:
        assert converters.normalize(input_uid) == input_uid
        assert all(converters.normalize(new_uid) == new_uid for new_uid in expected_new_uids)

        input_tag = TagInNormalization(
            uid=input_uid,
            parts=utils.uid_to_parts(input_uid),
            mode=NormalizationMode.preserve,
            link="http://example.com/tag",
            categories={TagCategory.feed_tag},
        )

        expected_new_tags = [
            RawTag(
                raw_uid=new_uid,
                normalization=NormalizationMode.raw,  # must be raw for all derived tags
                link=input_tag.link,
                categories=input_tag.categories,
            )
            for new_uid in expected_new_uids
        ]

        can_continue, new_tags = await normalizer.normalize(input_tag)

        assert can_continue == expected_continue
        assert new_tags == expected_new_tags
