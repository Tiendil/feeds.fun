import os
import pytest
import time
import sys

from ffun.domain.entities import TagUid
from ffun.ontology.entities import NormalizationMode, RawTag
from ffun.tags import converters, utils
from ffun.tags.entities import TagCategory, TagInNormalization
from ffun.tags.normalizers import form_normalizer

normalizer = form_normalizer.Normalizer()


class TestNormalizer:
    @pytest.mark.parametrize(
        "input_uid, expected_tag_valid, expected_new_uids",
        [
            ("", False, []),

            ("reviews", False, ["review"]),
            ("review", True, []),

            ("book-reviews", False, ["book-review"]),
            ("books-review", False, ["book-review"]),
            ("books-reviews", False, ["book-review"]),
            ("book-review", True, []),

# base tail multiple meaning -> tax taxis

            # ("sales-tax", True, []),
            # ("sale-taxes", False, ["sales-tax"]),
            # ("sales-taxes", False, ["sales-tax"]),
            # ("sale-tax", False, ["sales-tax"]),

# base tail multiple forms -> design (noun), designs (verb)

            ("system-design", False, ["systems-design"]),
            ("systems-design", True, []),
            # ("system-designs", False, ["systems-design"]),
            # ("systems-designs", False, ["systems-design"]),

# just wrong form

            ("systems-engineering", True, []),
            ("system-engineering", False, ["systems-engineering"]),

            ("operation-research", False, ["operations-research"]),
            ("operations-research", True, []),
            ("operations-researches", False, ["operations-research"]),
            ("operation-researches", False, ["operations-research"]),

            ("consumer-goods-sector", True, []),
            ("consumers-good-sector", False, ["consumer-goods-sector"]),
            ("consumers-goods-sector", False, ["consumer-goods-sector"]),
            ("consumer-good-sector", False, ["consumer-goods-sector"]),

            ("consumer-goods-sectors", False, ["consumer-goods-sector"]),
            ("consumers-good-sectors", False, ["consumer-goods-sector"]),
            ("consumers-goods-sectors", False, ["consumer-goods-sector"]),
            ("consumer-good-sectors", False, ["consumer-goods-sector"]),

            ("charles-darwin", True, []),
            ("new-york", True, []),

            ("scissors-case", True, []),
            ("scissors-cases", False, ["scissors-case"]),

            ("pants-pocket", True, []),
            ("pant-pocket", False, ["pants-pocket"]),
            ("pants-pockets", False, ["pants-pocket"]),
            ("pant-pockets", False, ["pants-pocket"]),
        ],
    )
    @pytest.mark.asyncio
    async def test(self, input_uid: TagUid, expected_tag_valid: bool, expected_new_uids: list[str]) -> None:
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

        tag_valid, new_tags = await normalizer.normalize(input_tag)

        new_tags.sort(key=lambda t: t.raw_uid)
        expected_new_tags.sort(key=lambda t: t.raw_uid)

        # print(tag_valid, expected_tag_valid)
        # print(new_tags, expected_new_tags)
        assert tag_valid == expected_tag_valid
        assert new_tags == expected_new_tags

    # @pytest.mark.skipif(reason="Performance test disabled by default.")
    @pytest.mark.asyncio
    async def test_performance(self) -> None:
        n = 10000

        input_tags = [
            TagInNormalization(
                uid=input_uid,
                parts=utils.uid_to_parts(input_uid),
                mode=NormalizationMode.preserve,
                link="http://example.com/tag",
                categories={TagCategory.feed_tag},
            )
            for input_uid in [
                "book-cover-review", "book-covers-review", "book-cover-reviews", "books-cover-reviews",
                "sale-tax-holiday", "sales-tax-holiday", "sales-taxes-holidays",
                "system-integration-test", "systems-integration-tests",
                "data-pipeline", "data-pipelines", "analytics-platform", "analytics-platforms",
                "market-trend", "market-trends",
            ] * n
        ]

        # warm up

        for input_tag in input_tags:
            await normalizer.normalize(input_tag)

        # measure

        start = time.perf_counter()

        for input_tag in input_tags:
            await normalizer.normalize(input_tag)

        elapsed = time.perf_counter() - start

        # report

        total = len(input_tags)
        rate = total / elapsed if elapsed > 0 else float("inf")

        print("\n=== Performance ===")
        print(f"items: {total}")
        print(f"time_sec: {elapsed:.6f}")
        print(f"throughput_tags_per_sec: {rate:.2f}")

        assert False
