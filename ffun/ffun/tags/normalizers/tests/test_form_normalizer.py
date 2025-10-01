import sys
import time

import pytest

from ffun.domain.entities import TagUid
from ffun.ontology.entities import NormalizationMode, RawTag
from ffun.tags import converters, utils
from ffun.tags.entities import TagCategory, TagInNormalization
from ffun.tags.normalizers import form_normalizer

normalizer = form_normalizer.Normalizer()


class TestNormalizer:
    # not-so-good cases marked with "(?)"
    # really-bad-cases additionally marked with [bad]
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
            ("sales-tax", True, []),
            ("sale-taxes", False, ["sales-tax"]),
            ("sales-taxes", False, ["sales-tax"]),
            ("sale-tax", False, ["sales-tax"]),
            # multiple tail meanings: axe/axis
            ("gravity-axes", False, ["gravity-axis"]),
            ("wooden-axes", False, ["wooden-axe"]),
            # base tail multiple forms -> design (noun), designs (verb)
            ("system-design", False, ["systems-design"]),
            ("systems-design", True, []),
            ("system-designs", False, ["systems-design"]),
            ("systems-designs", False, ["systems-design"]),
            # just wrong form
            ("systems-engineering", True, []),
            ("system-engineering", False, ["systems-engineering"]),
            ("operation-research", False, ["operations-research"]),
            ("operations-research", True, []),
            ("operations-researches", False, ["operations-research"]),
            ("operation-researches", False, ["operations-research"]),
            ("consumer-goods-sector", False, ["consumer-goods-sectors"]),
            ("consumers-good-sector", False, ["consumer-goods-sectors"]),
            ("consumers-goods-sector", False, ["consumer-goods-sectors"]),
            ("consumer-good-sector", False, ["consumer-goods-sectors"]),
            ("consumer-goods-sectors", True, []),
            ("consumers-good-sectors", False, ["consumer-goods-sectors"]),
            ("consumers-goods-sectors", False, ["consumer-goods-sectors"]),
            ("consumer-good-sectors", False, ["consumer-goods-sectors"]),
            ("charles-darwin", True, []),
            ("new-york", True, []),
            ("scissors-case", True, []),
            ("scissors-cases", False, ["scissors-case"]),
            ("pants-pocket", False, ["pant-pockets"]),  # (?)
            ("pant-pocket", False, ["pant-pockets"]),  # (?)
            ("pants-pockets", False, ["pant-pockets"]),  # (?)
            ("pant-pockets", True, []),  # (?)
            # Pluralia tantum and invariant "s"-final nouns at tail
            ("world-news", True, []),  # 'news' invariant
            ("news-analysis", True, []),
            ("tv-series", True, []),  # series invariant
            ("animal-species", False, ["animals-species"]),  # species invariant (?)
            ("company-headquarters", True, []),  # headquarters invariant
            ("means-test", False, ["mean-test"]),  # means invariant (sing=plural) (?)
            # (?) this is an interesting example, both
            # public-work and work-department prefere singular "work"
            # but together they require plural "works" in "public-works-department"
            # because it is a fixed term
            # Making such transition is not the goal of this normalizer
            # Most likely they should be handled as a verbose tag names for the user
            ("public-works-department", False, ["public-work-department"]),
            ("arms-control", False, ["arm-control"]),  # 'arms' pluralia tantum (weapons) (?) [bad]
            ("earnings-report", True, []),  # 'earnings' as fixed financial term
            # Pair nouns and clothing/tools that are conceptually plural
            ("glasses-case", False, ["glass-case"]),  # (?) [bad]
            ("spectacles-case", False, ["spectacles-cases"]),
            ("pliers-holder", True, []),
            ("tongs-stand", True, []),
            ("shorts-pocket", False, ["shorts-pockets"]),  # (?)
            ("binoculars-strap", False, ["binoculars-straps"]),  # (?)
            # Latin/Greek irregulars (tail singularization + mid/first alignment)
            ("price-indices", False, ["price-index"]),
            ("search-criteria", True, []),  # (?)
            ("bug-criteria", False, ["bug-criterion"]),
            ("weather-phenomena", True, []),  # (?)
            ("lab-data", True, []),  # accept data as head (common modern usage)
            ("media-studies", True, []),
            ("media-study", False, ["media-studies"]),
            ("bacteria-culture", False, ["bacteria-cultures"]),  # (?)
            ("alumni-network", True, []),
            # Alumn is a borrowed Latin word, it has several irregular forms
            # maybe we should add variations for gender in our logic
            ("alumnus-profiles", False, ["alumni-profiles"]),  # (?)
            # Ambiguous/irregular tails (axes/leaves/dice/mice/geese/children)
            ("routing-axes", False, ["routing-axis"]),
            ("kitchen-axes", False, ["kitchen-axe"]),
            ("autumn-leaves-color", False, ["autumn-leaf-color"]),  # leaves intended (plural) (?)
            ("leaf-springs", False, ["leaf-spring"]),
            ("tabletop-dice", True, []),  # dice often mass/plural; modifier usage ok
            ("dice-game", True, []),
            ("die-cast-models", True, []),
            ("field-mice-population", False, ["fields-mice-populations"]),  # (?) [bad] "field mice" is a single term
            ("geese-migration", True, []),
            ("children-hospital", False, ["child-hospital"]),  # (?)
            ("children-book", False, ["children-books"]),
            # Fixed academic/professional fields that look plural
            ("economics-textbook", True, []),
            ("physics-lab", True, []),
            ("mathematics-olympiad", True, []),
            ("analytics-pipeline", True, []),
            ("logistics-center", False, ["logistics-centers"]),
            ("ethics-review", True, []),
            ("statistics-course", True, []),
            # Proper nouns with deceptive plural/singular shapes
            (
                "new-york-times-article",
                False,
                ["new-york-time-article"],
            ),  # (?) [bad] "New York Times" is a single term
            # (?) this noralizer should not get "the" on its input
            # => the problem is not such big.
            ("the-beatles-album", False, ["thes-beatles-albums"]),
            ("google-analytics-event", False, ["google-analytics-events"]),
            ("united-states-visa", True, []),
            # Acronyms, numerals, version tokens at tail (should remain untouched)
            ("user-api", True, []),
            ("user-api-development", True, []),
            ("users-api", False, ["user-api"]),
            ("system-cli", True, []),
            ("systems-cli", False, ["system-cli"]),
            ("design-patterns-101", False, ["designs-patterns-101"]),  # (?) [bad]
            ("release-notes-2025", False, ["releases-notes-2025"]),  # (?) [bad]
            # roman numerals
            ("chapter-ii", True, []),
            ("chapter-iii", True, []),
            ("chapter-xxvi", True, []),
            # Non-head pluralization (plural attaches away from tail)
            ("attorneys-general", False, ["attorney-general"]),
            ("mothers-in-law", False, ["mother-in-law"]),
            ("passers-by", True, []),  # (?)
            ("editors-in-chief", False, ["editor-in-chief"]),
            ("courts-martial", True, []),  # (?)
            # a-b-c chains where a↔c cohesion should dominate (semantic head = c)
            # Expect your cosine chain to prefer forms of 'a' that better match 'c', even if 'b' drifts.
            ("chicken-soup-recipe", True, []),  # keep 'recipe' singular; 'chicken-soup' unit
            ("machine-learning-systems", True, []),
            ("machine-learnings-system", False, ["machine-learning-systems"]),
            ("search-result-page", False, ["search-results-page"]),
            ("search-results-page", True, []),
            ("price-index-method", True, []),  # 'price' ↔ 'method' stronger than 'price'↔'index' here
            ("risk-factor-model", False, ["risk-factors-models"]),  # (?) "risk factor" is a single term
            ("risk-factors-model", False, ["risk-factors-models"]),  # (?) "risk factor" is a single term
            ("image-feature-extractor", False, ["images-feature-extractor"]),
            ("images-features-extractor", False, ["images-feature-extractor"]),
            ("time-series-forecast", False, ["times-series-forecasts"]),  # (?) "time series" is a single term
            ("time-series-forecasts", False, ["times-series-forecasts"]),  # (?) "time series" is a single term
            ("customer-support-ticket", True, []),
            ("customers-support-tickets", False, ["customer-support-ticket"]),
            # Heads that should remain plural because of idiom/fixed sense
            ("table-of-contents", False, ["table-of-content"]),  # (?) "table of contents" is a single term
            ("earnings-per-share", True, []),
            ("goods-and-services-tax", False, ["good-and-services-tax"]),  # (?) [bad]
            # Multi-sense middles and tails to test cosine disambiguation
            ("paper-leaves-collection", False, ["paper-leaf-collection"]),  # (?)
            # these tags contain constant tag parts from tag.converters => they should not be changed
            ("example-dot-com", True, []),
            ("c-plus-plus-development", True, []),
            ("c-sharp-tutorial", True, []),
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

        assert tag_valid == expected_tag_valid
        assert new_tags == expected_new_tags

    @pytest.mark.skipif(reason="Performance test disabled by default.")
    @pytest.mark.asyncio
    async def test_performance(self) -> None:
        n = 10000

        input_tags = [
            TagInNormalization(
                uid=TagUid(input_uid),
                parts=utils.uid_to_parts(TagUid(input_uid)),
                mode=NormalizationMode.preserve,
                link="http://example.com/tag",
                categories={TagCategory.feed_tag},
            )
            for input_uid in [
                "book-cover-review",
                "book-covers-review",
                "book-cover-reviews",
                "books-cover-reviews",
                "sale-tax-holiday",
                "sales-tax-holiday",
                "sales-taxes-holidays",
                "system-integration-test",
                "systems-integration-tests",
                "data-pipeline",
                "data-pipelines",
                "analytics-platform",
                "analytics-platforms",
                "market-trend",
                "market-trends",
                "gravity-axes",
                "wooden-axes",
                "long-gravity-axes",
                "long-wooden-axes",
            ]
            * n
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

        sys.stdout.write("\n=== Performance ===\n")
        sys.stdout.write(f"items: {total}\n")
        sys.stdout.write(f"time_sec: {elapsed:.6f}\n")
        sys.stdout.write(f"throughput_tags_per_sec: {rate:.2f}\n")

        sys.stdout.write(f"Cos cache info: {normalizer.cache()._cached_cos_rows.cache_info()}\n")
        sys.stdout.write(f"Words cache info: {normalizer.cache()._cached_get_word_forms.cache_info()}\n")

        assert False
