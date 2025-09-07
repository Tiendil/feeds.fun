import pytest

from ffun.domain.entities import TagUid
from ffun.ontology.entities import NormalizedTag, RawTag, TagCategory
from ffun.tags.domain import normalize


# TODO: move initial conversion tests into a separate class
# TODO: test logic without normalizers
class TestNormalize:

    @pytest.mark.asyncio
    async def test_no_tags(self) -> None:
        assert await normalize([]) == []

    @pytest.mark.parametrize(
        "raw_uid,norm_uid",
        [
            ("tag-1", TagUid("tag-1")),
            ("taG-2", TagUid("tag-2")),
            ("tag--3", TagUid("tag-3")),
        ],
    )
    @pytest.mark.asyncio
    async def test_single_tag(self, raw_uid: str, norm_uid: TagUid) -> None:
        assert await normalize([RawTag(raw_uid=raw_uid, preserve=False)]) == [NormalizedTag(uid=norm_uid)]

    @pytest.mark.asyncio
    async def test_normalize_complex(self) -> None:
        input = [
            RawTag(raw_uid="tag--1", preserve=False),
            RawTag(raw_uid="tag-2", preserve=False),
            RawTag(raw_uid="taG-3", preserve=False),
            RawTag(raw_uid="tag-4", preserve=False),
            RawTag(raw_uid="tag--5", preserve=False),
        ]

        expected = [
            NormalizedTag(uid=TagUid("tag-1")),
            NormalizedTag(uid=TagUid("tag-2")),
            NormalizedTag(uid=TagUid("tag-3")),
            NormalizedTag(uid=TagUid("tag-4")),
            NormalizedTag(uid=TagUid("tag-5")),
        ]

        assert await normalize(input) == expected

    @pytest.mark.asyncio
    async def test_copy_properties(self) -> None:
        input = [
            RawTag(
                raw_uid="tag-1",
                preserve=False,
                name="Tag One",
                link="http://example.com/tag1",
                categories={TagCategory.network_domain},
            ),
            RawTag(
                raw_uid="tag-2",
                preserve=False,
                name="Tag Two",
                link="http://example.com/tag2",
                categories={TagCategory.feed_tag},
            ),
        ]

        expected = [
            NormalizedTag(
                uid=TagUid("tag-1"),
                name="Tag One",
                link="http://example.com/tag1",
                categories={TagCategory.network_domain},
            ),
            NormalizedTag(
                uid=TagUid("tag-2"),
                name="Tag Two",
                link="http://example.com/tag2",
                categories={TagCategory.feed_tag},
            ),
        ]

        assert await normalize(input) == expected

    @pytest.mark.asyncio
    async def test_remove_duplicates(self) -> None:
        input = [
            RawTag(raw_uid="tag-1", preserve=False),
            RawTag(raw_uid="tag-1", preserve=False),
            RawTag(raw_uid="tag-2", preserve=False),
            RawTag(raw_uid="tag-3", preserve=False),
            RawTag(raw_uid="tag-2", preserve=False),
        ]

        expected = [
            NormalizedTag(uid=TagUid("tag-1")),
            NormalizedTag(uid=TagUid("tag-2")),
            NormalizedTag(uid=TagUid("tag-3")),
        ]

        assert await normalize(input) == expected
