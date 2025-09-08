import pytest

from ffun.domain.entities import TagUid
from ffun.ontology.entities import NormalizationMode, RawTag
from ffun.tags import converters, utils
from ffun.tags.entities import TagCategory, TagInNormalization
from ffun.tags.normalizers import part_replacer

normalizer = part_replacer.Normalizer(replacements={"start-up": "startup", "set-up": "setup", "em": "them"})


class TestNormalizer:
    @pytest.mark.parametrize(
        "input_uid, expected_continue, expected_new_uids",
        [
            ("", False, []),
            ("nohtingtodo", True, []),
            ("nohting-to-do", True, []),
            ("set-up-for-success", False, ["setup-for-success"]),
            ("best-start-up-ever", False, ["best-startup-ever"]),
            ("how-to-start-up", False, ["how-to-startup"]),
            ("let-set-up-for-start-up", False, ["let-setup-for-start-up", "let-set-up-for-startup"]),
            ("let-start-up-start-up", False, ["let-startup-startup"]),
            ("let-start-up-or-not-start-up", False, ["let-startup-or-not-startup"]),
            ("let-em-go", False, ["let-them-go"]),
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

        new_tags.sort(key=lambda t: t.raw_uid)
        expected_new_tags.sort(key=lambda t: t.raw_uid)

        assert can_continue == expected_continue
        assert new_tags == expected_new_tags
