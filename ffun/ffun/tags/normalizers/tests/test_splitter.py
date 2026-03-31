import pytest

from ffun.domain.entities import TagUid
from ffun.ontology.entities import RawTag
from ffun.tags import converters, utils
from ffun.tags.entities import NormalizationMode, TagCategory, TagInNormalization
from ffun.tags.normalizers import splitter

normalizer = splitter.Normalizer(separators=["for", "impact-on", "через", "влияние-на"])


class TestNormalizer:
    @pytest.mark.parametrize(
        "unicode, input_uid, expected_continue, expected_new_uids",
        [
            (False, "", False, []),
            (False, "nohtingtodo", True, []),
            (False, "nohting-to-do", True, []),
            (False, "checkforinside", True, []),
            (False, "checkimpact-oninside", True, []),
            (False, "set-up-for-success", False, ["set-up", "success"]),
            (False, "for-x", False, ["x"]),
            (False, "x-for-y", False, ["x", "y"]),
            (False, "x-for", False, ["x"]),
            (False, "social-media-impact-on-innovation", False, ["social-media", "innovation"]),
            (False, "impact-on-innovation", False, ["innovation"]),
            (
                False,
                "rest-api-for-graph-processing-impact-on-innovation",
                False,
                ["rest-api", "graph-processing-impact-on-innovation", "rest-api-for-graph-processing", "innovation"],
            ),
            (False, "for-impact-on", False, ["impact-on", "for"]),
            (False, "for-for-impact-on", False, ["for", "for-impact-on", "for-for", "impact-on"]),
            (False, "x-for-y-for-z", False, ["x", "z", "y-for-z", "x-for-y"]),
            (
                False,
                "impact-on-x-impact-on-y-impact-on",
                False,
                ["x-impact-on-y-impact-on", "impact-on-x", "y-impact-on", "impact-on-x-impact-on-y"],
            ),
            (False, "x-impact-on-impact-on-y", False, ["x", "impact-on-y", "x-impact-on", "y"]),
            (
                False,
                "for-for-impact-on-impact-on",
                False,
                ["for", "for-for", "impact-on-impact-on", "impact-on", "for-impact-on-impact-on", "for-for-impact-on"],
            ),
            (True, "café-for-bistro", False, ["café", "bistro"]),
            (True, "for-café", False, ["café"]),
            (True, "данные-for-аналитика", False, ["данные", "аналитика"]),
            (True, "привет-impact-on-мир", False, ["привет", "мир"]),
            (True, "impact-on-метрика", False, ["метрика"]),
            (True, "данные-через-аналитика", False, ["данные", "аналитика"]),
            (True, "через-метрика", False, ["метрика"]),
            (True, "привет-влияние-на-мир", False, ["привет", "мир"]),
            (True, "влияние-на-метрика", False, ["метрика"]),
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
