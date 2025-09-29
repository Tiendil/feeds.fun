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

            # Pluralia tantum and invariant "s"-final nouns at tail
            ("world-news", True, []),                                    # 'news' invariant
            ("news-analysis", True, []),
            ("tv-series", True, []),                                      # series invariant
            # ("animal-species", True, []),                                 # species invariant
            ("company-headquarters", True, []),                           # headquarters invariant
            # ("means-test", True, []),                                     # means invariant (sing=plural)
            # ("public-works-department", True, []),                        # 'works' fixed term, do not singularize
            # ("arms-control", True, []),                                   # ??? 'arms' pluralia tantum (weapons)
            ("earnings-report", True, []),                                # 'earnings' as fixed financial term

            # Pair nouns and clothing/tools that are conceptually plural
            # ("glasses-case", True, []),   # ???
            # ("spectacles-case", True, []),
            ("pliers-holder", True, []),
            ("tongs-stand", True, []),
            ("shorts-pocket", True, []),
            ("binoculars-strap", True, []),

            # Latin/Greek irregulars (tail singularization + mid/first alignment)
            ("price-indices", False, ["price-index"]),
            ("search-criteria", False, ["search-criterion"]),             # strict grammar
            ("bug-criteria", False, ["bug-criterion"]),
            ("weather-phenomena", False, ["weather-phenomenon"]),
            ("lab-data", True, []),                                       # accept data as head (common modern usage)
            # ("media-studies", True, []),                                  # 'studies' as field; tail plural but fixed term
            ("bacteria-culture", True, []),                               # correct already (tail singular)
            ("alumni-network", True, []),                                 # alumni as modifier is fine
            # ("alumnus-profiles", False, ["alumnus-profile"]),             # regularize tail

            # Ambiguous/irregular tails (axes/leaves/dice/mice/geese/children)
            ("routing-axes", False, ["routing-axis"]),
            # ("kitchen-axes", False, ["kitchen-axe"]),    # ????
            # ("autumn-leaves-color", True, []),                            # leaves intended (plural) but modifier; tail =  color
            ("leaf-springs", False, ["leaf-spring"]),
            ("tabletop-dice", True, []),                                  # dice often mass/plural; modifier usage ok
            ("dice-game", True, []),
            ("die-cast-models", False, ["die-cast-model"]),               # tail singularize
            # ("field-mice-population", True, []),                          # ??? mice as modifier ok; tail = population
            ("geese-migration", True, []),
            # ("children-hospital", False, ["childrens-hospital"]),         # real term is "children's hospital" -> approximate
            # ("children-book", False, ["childrens-book"]),                 # same note; your hyphen grammar can choose policy

            # Fixed academic/professional fields that look plural
            ("economics-textbook", True, []),
            ("physics-lab", True, []),
            ("mathematics-olympiad", True, []),
            ("analytics-pipeline", True, []),
            ("logistics-center", True, []),
            ("ethics-review", True, []),
            ("statistics-course", True, []),

            # Proper nouns with deceptive plural/singular shapes
            # ("new-york-times-article", True, []),                         # !!! (word dependent from left & right) 'times' is part of name
            # ("the-beatles-album", True, []),
            ("google-analytics-event", True, []),
            ("united-states-visa", True, []),                             # 'states' is proper name component

            # Acronyms, numerals, version tokens at tail (should remain untouched)
            # ("user-api", True, []),  # !!!
            # ("users-api", False, ["user-api"]),
            # ("system-cli", True, []),
            # ("systems-cli", False, ["system-cli"]),
            # ("design-patterns-101", True, []),  # ??? How to behave in that case? when tail has no vector?
            # ("release-notes-2025", True, []),  # ???
            ("chapter-ii", True, []),                                     # roman numerals
            ("chapter-iii", True, []),

            # Non-head pluralization (plural attaches away from tail)
            ("attorneys-general", False, ["attorney-general"]),
            ("mothers-in-law", False, ["mother-in-law"]),
            # ("passers-by", False, ["passer-by"]),  # ??? again, no vector for 'by'
            ("editors-in-chief", False, ["editor-in-chief"]),
            # ("courts-martial", False, ["court-martial"]),

            # a-b-c chains where a↔c cohesion should dominate (semantic head = c)
            # Expect your cosine chain to prefer forms of 'a' that better match 'c', even if 'b' drifts.
            ("chicken-soup-recipe", True, []),                            # keep 'recipe' singular; 'chicken-soup' unit
            ("machine-learning-system", True, []),                        # tail singular, b = learning (verb-noun)
            ("machine-learnings-system", False, ["machine-learning-system"]),
            # ("search-result-page", True, []),                      # !!! word depends from left and right  # classic SRP
            # ("search-results-page", False, ["search-result-page"]),
            ("price-index-method", True, []),                             # 'price' ↔ 'method' stronger than 'price'↔'index' here
            ("risk-factor-model", True, []),
            ("risk-factors-model", False, ["risk-factor-model"]),
            # ("image-feature-extractor", True, []),
            # ("images-features-extractor", False, ["image-feature-extractor"]),
            # ("time-series-forecast", True, []),   # ???                        # 'series' invariant mid; tail singular
            # ("time-series-forecasts", False, ["time-series-forecast"]),
            ("customer-support-ticket", True, []),
            ("customers-support-tickets", False, ["customer-support-ticket"]),

            # Heads that should remain plural because of idiom/fixed sense
            # ("table-of-contents", True, []),                              # 'contents' fixed
            ("earnings-per-share", True, []),
            # ("goods-and-services-tax", True, []),

            # Multi-sense middles and tails to test cosine disambiguation
            # ("paper-leaves-collection", True, []),

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

        print(tag_valid, expected_tag_valid)
        print(new_tags, expected_new_tags)
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
                "market-trend", "market-trends", "gravity-axes", "wooden-axes", "long-gravity-axes",
                "long-wooden-axes",
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
