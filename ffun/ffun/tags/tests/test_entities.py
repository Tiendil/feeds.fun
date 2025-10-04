import pytest

from ffun.domain.entities import TagUid, TagUidPart
from ffun.tags.entities import NormalizationMode, TagCategory, TagInNormalization


class TestTagInNormalization:

    @pytest.mark.parametrize("category", TagCategory)
    def test_each_tag_category_has_mode(self, category: TagCategory) -> None:
        tag = TagInNormalization(
            uid=TagUid("example-tag"),
            parts=[TagUidPart("example"), TagUidPart("tag")],
            link=None,
            categories={category},
        )

        assert tag.mode in NormalizationMode
