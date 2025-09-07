import pytest

from ffun.domain.entities import TagUid
from ffun.ontology.entities import NormalizedTag, RawTag, TagCategory
from ffun.tags.domain import normalize, apply_normalizers
from ffun.tags.entities import TagInNormalization
from ffun.tags.utils import uid_to_parts
from ffun.tags.normalizers import FakeNormalizer, NormalizerAlwaysError, NormalizerInfo


class TestApplyNormalizers:

    @pytest.fixture
    def tag(self) -> TagInNormalization:
        uid: TagUid = "example-tag"
        return TagInNormalization(
            uid=uid,
            parts=uid_to_parts(uid),
            preserve=True,
            link=None,
            categories={TagCategory.feed_tag},
        )

    @pytest.fixture
    def raw_tags(self) -> list[RawTag]:
        return [RawTag(
            raw_uid=f"new-tag-{i}",
            preserve=False,
            link=None,
            categories={TagCategory.feed_tag},
        ) for i in range(1, 4)]

    @pytest.mark.asyncio
    async def test_no_normalizers(self, tag: TagInNormalization) -> None:
        tag_valid, new_tags = await apply_normalizers([], tag)
        assert tag_valid
        assert new_tags == []

    @pytest.mark.parametrize("tag_valid", [True, False])
    @pytest.mark.asyncio
    async def test_single_normalizer__preserve(self, tag_valid: bool, tag: TagInNormalization, raw_tags: list[RawTag]) -> None:
        tag = tag.replace(preserve=True)

        normalizer = FakeNormalizer(tag_valid, raw_tags)
        info = NormalizerInfo(id=1, name="fake", normalizer=normalizer)

        result_tag_valid, new_tags = await apply_normalizers([info], tag)
        assert result_tag_valid
        assert new_tags == raw_tags

    @pytest.mark.parametrize("tag_valid", [True, False])
    @pytest.mark.asyncio
    async def test_single_normalizer__not_preserve(self, tag_valid: bool, tag: TagInNormalization, raw_tags: list[RawTag]) -> None:
        tag = tag.replace(preserve=False)

        normalizer = FakeNormalizer(tag_valid, raw_tags)
        info = NormalizerInfo(id=1, name="fake", normalizer=normalizer)

        result_tag_valid, new_tags = await apply_normalizers([info], tag)
        assert tag_valid == result_tag_valid
        assert new_tags == raw_tags

    @pytest.mark.asyncio
    async def test_chain_of_normalizers__preserve(self, tag: TagInNormalization, raw_tags: list[RawTag]) -> None:
        tag = tag.replace(preserve=True)

        normalizers = [FakeNormalizer(True, [raw_tags[0]]),
                       FakeNormalizer(False, [raw_tags[1]]),
                       FakeNormalizer(True, [raw_tags[2]])]
        infos = [NormalizerInfo(id=i, name=f"fake-{i}", normalizer=normalizer)
                 for i, normalizer in enumerate(normalizers, start=1)]

        result_tag_valid, new_tags = await apply_normalizers(infos, tag)
        assert result_tag_valid
        assert new_tags == raw_tags

    @pytest.mark.asyncio
    async def test_chain_of_normalizers__not_preserve(self, tag: TagInNormalization, raw_tags: list[RawTag]) -> None:
        tag = tag.replace(preserve=False)

        normalizers = [FakeNormalizer(True, [raw_tags[0]]),
                       FakeNormalizer(False, [raw_tags[1]]),
                       FakeNormalizer(True, [raw_tags[2]])]
        infos = [NormalizerInfo(id=i, name=f"fake-{i}", normalizer=normalizer)
                 for i, normalizer in enumerate(normalizers, start=1)]

        result_tag_valid, new_tags = await apply_normalizers(infos, tag)
        assert not result_tag_valid
        assert new_tags == raw_tags[0:2]

    @pytest.mark.asyncio
    async def test_chain_of_normalizers__full_pass(self, tag: TagInNormalization, raw_tags: list[RawTag]) -> None:
        normalizers = [FakeNormalizer(True, [raw_tags[0]]),
                       FakeNormalizer(True, [raw_tags[1]]),
                       FakeNormalizer(True, [raw_tags[2]])]
        infos = [NormalizerInfo(id=i, name=f"fake-{i}", normalizer=normalizer)
                 for i, normalizer in enumerate(normalizers, start=1)]

        result_tag_valid, new_tags = await apply_normalizers(infos, tag)
        assert result_tag_valid
        assert new_tags == raw_tags

    @pytest.mark.asyncio
    async def test_error_in_normalizer(self, tag: TagInNormalization) -> None:
        class FakeException(BaseException):
            pass

        normalizer = NormalizerAlwaysError(FakeException("test error"))
        info = NormalizerInfo(id=1, name="fake", normalizer=normalizer)

        result_tag_valid, new_tags = await apply_normalizers([info], tag)
        assert result_tag_valid
        assert new_tags == []


# class TestNormalize:

#     @pytest.mark.asyncio
#     async def test_no_tags(self) -> None:
#         assert await normalize([]) == []

#     @pytest.mark.parametrize(
#         "raw_uid,norm_uid",
#         [
#             ("tag-1", TagUid("tag-1")),
#             ("taG-2", TagUid("tag-2")),
#             ("tag--3", TagUid("tag-3")),
#         ],
#     )
#     @pytest.mark.asyncio
#     async def test_single_tag(self, raw_uid: str, norm_uid: TagUid) -> None:
#         assert await normalize([RawTag(raw_uid=raw_uid, preserve=False)]) == [NormalizedTag(uid=norm_uid)]

#     @pytest.mark.asyncio
#     async def test_normalize_complex(self) -> None:
#         input = [
#             RawTag(raw_uid="tag--1", preserve=False),
#             RawTag(raw_uid="tag-2", preserve=False),
#             RawTag(raw_uid="taG-3", preserve=False),
#             RawTag(raw_uid="tag-4", preserve=False),
#             RawTag(raw_uid="tag--5", preserve=False),
#         ]

#         expected = [
#             NormalizedTag(uid=TagUid("tag-1")),
#             NormalizedTag(uid=TagUid("tag-2")),
#             NormalizedTag(uid=TagUid("tag-3")),
#             NormalizedTag(uid=TagUid("tag-4")),
#             NormalizedTag(uid=TagUid("tag-5")),
#         ]

#         assert await normalize(input) == expected

#     @pytest.mark.asyncio
#     async def test_copy_properties(self) -> None:
#         input = [
#             RawTag(
#                 raw_uid="tag-1",
#                 preserve=False,
#                 name="Tag One",
#                 link="http://example.com/tag1",
#                 categories={TagCategory.network_domain},
#             ),
#             RawTag(
#                 raw_uid="tag-2",
#                 preserve=False,
#                 name="Tag Two",
#                 link="http://example.com/tag2",
#                 categories={TagCategory.feed_tag},
#             ),
#         ]

#         expected = [
#             NormalizedTag(
#                 uid=TagUid("tag-1"),
#                 name="Tag One",
#                 link="http://example.com/tag1",
#                 categories={TagCategory.network_domain},
#             ),
#             NormalizedTag(
#                 uid=TagUid("tag-2"),
#                 name="Tag Two",
#                 link="http://example.com/tag2",
#                 categories={TagCategory.feed_tag},
#             ),
#         ]

#         assert await normalize(input) == expected

#     @pytest.mark.asyncio
#     async def test_remove_duplicates(self) -> None:
#         input = [
#             RawTag(raw_uid="tag-1", preserve=False),
#             RawTag(raw_uid="tag-1", preserve=False),
#             RawTag(raw_uid="tag-2", preserve=False),
#             RawTag(raw_uid="tag-3", preserve=False),
#             RawTag(raw_uid="tag-2", preserve=False),
#         ]

#         expected = [
#             NormalizedTag(uid=TagUid("tag-1")),
#             NormalizedTag(uid=TagUid("tag-2")),
#             NormalizedTag(uid=TagUid("tag-3")),
#         ]

#         assert await normalize(input) == expected
