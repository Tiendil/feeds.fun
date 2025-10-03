from typing import Any

import pytest
from pytest_mock import MockerFixture

from ffun.domain.entities import TagUid, TagUidPart
from ffun.ontology.entities import NormalizedTag, RawTag, TagCategory
from ffun.tags.domain import apply_normalizers, normalize, prepare_for_normalization
from ffun.tags.entities import TagInNormalization, TagCategory, NormalizationMode
from ffun.tags.normalizers import FakeNormalizer, NormalizerAlwaysError, NormalizerInfo
from ffun.tags.utils import uid_to_parts


class TestTagInNormalization:

    @pytest.mark.parametrize("category", TagCategory)
    def test_each_tag_category_has_mode(self, category: TagCategory) -> None:
        tag = TagInNormalization(
            uid=TagUid("example-tag"),
            parts=[TagUidPart("example"), TagUidPart("tag")],
            link=None,
            categories={category}
        )

        assert tag.mode in NormalizationMode
