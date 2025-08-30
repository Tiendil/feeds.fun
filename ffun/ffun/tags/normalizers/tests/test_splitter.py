
import pytest

from ffun.tags.normalizers import splitter
from ffun.tags import utils, converters
from ffun.tags.entities import TagCategory, TagInNormalization
from ffun.ontology.entities import RawTag


normalizer = splitter.Normalizer(separators=['for', 'impact-on'])


class TestNormalizer:
    @pytest.mark.parametrize(
        "input_uid, expected_continue, expected_new_uids",
        [
            ("", False, []),
            ('nohtingtodo', True, []),
            ('nohting-to-do', True, []),
            ('set-up-for-success', False, ["set-up", "success"]),
            ('for-x', False, ["x"]),
            ('x-for-y', False, ["x", "y"]),
            ('x-for', False, ["x"]),
            ('social-media-impact-on-innovation', False, ["social-media", "innovation"]),
            ("impact-on-innovation", False, ["innovation"]),
            ("rest-api-for-graph-processing-impact-on-innovation",
             False,
             ["rest-api", "graph-processing-impact-on-innovation", "rest-api-for-graph-processing", "innovation"]),
            ("for-impact-on", False, ["impact-on", "for"]),
            ("for-for-impact-on", False, ["impact-on", "for-for"]),
            ("x-for-y-for-z", False, ["x", "y", "z"]),
            ("impact-on-x-impact-on-y-impact-on", False, ["x", "y"]),
            ("x-impact-on-impact-on-y", False, ["x", "y"]),
            ("for-for-impact-on-impact-on", False, ["for-for", "impact-on-impact-on"]),
        ],
    )
    @pytest.mark.asyncio
    async def test(self, input_uid: str, expected_continue: bool, expected_new_uids: list[str]) -> None:
        assert converters.normalize(input_uid) == input_uid
        assert all(converters.normalize(new_uid) == new_uid for new_uid in expected_new_uids)

        input_tag = TagInNormalization(uid=input_uid,
                                       parts=utils.uid_to_parts(input_uid),
                                       preserve=True,
                                       name="Test Tag",
                                       link="http://example.com/tag",
                                       categories={TagCategory.feed_tag}
                                       )

        expected_new_tags = [
            TagInNormalization(uid=new_uid,
                               parts=utils.uid_to_parts(new_uid),
                               preserve=False,  # must be False for all derived tags
                               name=None,
                               link=input_tag.link,
                               categories=input_tag.categories
                               )
            for new_uid in expected_new_uids
        ]

        can_continue, new_tags = await normalizer.normalize(input_tag)

        new_tags.sort(key=lambda t: t.uid)
        expected_new_tags.sort(key=lambda t: t.uid)

        assert can_continue == expected_continue
        assert new_tags == expected_new_tags
