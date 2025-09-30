from typing import Any

import pytest
from pytest_mock import MockerFixture

from ffun.domain.entities import TagUid, TagUidPart
from ffun.ontology.entities import NormalizationMode, NormalizedTag, RawTag, TagCategory
from ffun.tags.domain import apply_normalizers, normalize, prepare_for_normalization
from ffun.tags.entities import TagInNormalization
from ffun.tags.normalizers import FakeNormalizer, NormalizerAlwaysError, NormalizerInfo
from ffun.tags.utils import uid_to_parts


class TestPrepareForNormalization:

    @pytest.mark.parametrize("mode", NormalizationMode)
    def test(self, mode: NormalizationMode) -> None:
        raw_tag = RawTag(
            raw_uid="Example----Tag",
            normalization=mode,
            link="http://example.com/tag",
            categories={TagCategory.feed_tag},
        )

        prepared_tag = prepare_for_normalization(raw_tag)

        assert prepared_tag == TagInNormalization(
            uid=TagUid("example-tag"),
            parts=[TagUidPart("example"), TagUidPart("tag")],
            mode=mode,
            link=raw_tag.link,
            categories=raw_tag.categories,
        )


class TestApplyNormalizers:

    @pytest.fixture
    def tag(self) -> TagInNormalization:
        uid: TagUid = TagUid("example-tag")
        return TagInNormalization(
            uid=uid,
            parts=uid_to_parts(uid),
            mode=NormalizationMode.preserve,
            link=None,
            categories={TagCategory.feed_tag},
        )

    @pytest.fixture
    def raw_tags(self) -> list[RawTag]:
        return [
            RawTag(
                raw_uid=f"new-tag-{i}",
                normalization=NormalizationMode.raw,
                link=None,
                categories={TagCategory.feed_tag},
            )
            for i in range(1, 4)
        ]

    @pytest.mark.asyncio
    async def test_no_normalizers(self, tag: TagInNormalization) -> None:
        tag_valid, new_tags = await apply_normalizers([], tag)
        assert tag_valid
        assert new_tags == []

    @pytest.mark.parametrize("tag_valid", [True, False])
    @pytest.mark.asyncio
    async def test_single_normalizer__preserve(
        self, tag_valid: bool, tag: TagInNormalization, raw_tags: list[RawTag]
    ) -> None:
        tag = tag.replace(mode=NormalizationMode.preserve)

        normalizer = FakeNormalizer(tag_valid, raw_tags)
        info = NormalizerInfo(id=1, name="fake", normalizer=normalizer)

        result_tag_valid, new_tags = await apply_normalizers([info], tag)
        assert result_tag_valid
        assert new_tags == raw_tags

    @pytest.mark.parametrize("tag_valid", [True, False])
    @pytest.mark.asyncio
    async def test_single_normalizer__raw(
        self, tag_valid: bool, tag: TagInNormalization, raw_tags: list[RawTag]
    ) -> None:
        tag = tag.replace(mode=NormalizationMode.raw)

        normalizer = FakeNormalizer(tag_valid, raw_tags)
        info = NormalizerInfo(id=1, name="fake", normalizer=normalizer)

        result_tag_valid, new_tags = await apply_normalizers([info], tag)
        assert tag_valid == result_tag_valid
        assert new_tags == raw_tags

    @pytest.mark.parametrize("tag_valid", [True, False])
    @pytest.mark.asyncio
    async def test_single_normalizer__final(
        self, tag_valid: bool, tag: TagInNormalization, raw_tags: list[RawTag]
    ) -> None:
        tag = tag.replace(mode=NormalizationMode.final)

        normalizer = FakeNormalizer(tag_valid, raw_tags)
        info = NormalizerInfo(id=1, name="fake", normalizer=normalizer)

        result_tag_valid, new_tags = await apply_normalizers([info], tag)
        assert result_tag_valid
        assert new_tags == []

    @pytest.mark.asyncio
    async def test_chain_of_normalizers__preserve(self, tag: TagInNormalization, raw_tags: list[RawTag]) -> None:
        tag = tag.replace(mode=NormalizationMode.preserve)

        normalizers = [
            FakeNormalizer(True, [raw_tags[0]]),
            FakeNormalizer(False, [raw_tags[1]]),
            FakeNormalizer(True, [raw_tags[2]]),
        ]
        infos = [
            NormalizerInfo(id=i, name=f"fake-{i}", normalizer=normalizer)
            for i, normalizer in enumerate(normalizers, start=1)
        ]

        result_tag_valid, new_tags = await apply_normalizers(infos, tag)
        assert result_tag_valid
        assert new_tags == raw_tags

    @pytest.mark.asyncio
    async def test_chain_of_normalizers__not_preserve(self, tag: TagInNormalization, raw_tags: list[RawTag]) -> None:
        tag = tag.replace(mode=NormalizationMode.raw)

        normalizers = [
            FakeNormalizer(True, [raw_tags[0]]),
            FakeNormalizer(False, [raw_tags[1]]),
            FakeNormalizer(True, [raw_tags[2]]),
        ]
        infos = [
            NormalizerInfo(id=i, name=f"fake-{i}", normalizer=normalizer)
            for i, normalizer in enumerate(normalizers, start=1)
        ]

        result_tag_valid, new_tags = await apply_normalizers(infos, tag)
        assert not result_tag_valid
        assert new_tags == raw_tags[0:2]

    @pytest.mark.asyncio
    async def test_chain_of_normalizers__full_pass(self, tag: TagInNormalization, raw_tags: list[RawTag]) -> None:
        normalizers = [
            FakeNormalizer(True, [raw_tags[0]]),
            FakeNormalizer(True, [raw_tags[1]]),
            FakeNormalizer(True, [raw_tags[2]]),
        ]
        infos = [
            NormalizerInfo(id=i, name=f"fake-{i}", normalizer=normalizer)
            for i, normalizer in enumerate(normalizers, start=1)
        ]

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


class TestNormalize:

    @pytest.fixture(autouse=True)
    def turn_of_tag_form_normalization(self, mocker: MockerFixture) -> None:
        def fake_normalize(_self: Any, _tag: TagInNormalization) -> tuple[bool, list[RawTag]]:
            return True, []

        mocker.patch("ffun.tags.normalizers.form_normalizer.Normalizer.normalize", new=fake_normalize)

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
        assert await normalize([RawTag(raw_uid=raw_uid, normalization=NormalizationMode.raw)]) == [
            NormalizedTag(uid=norm_uid, link=None, categories=set())
        ]

    @pytest.mark.asyncio
    async def test_normalize_complex(self) -> None:
        input = [
            RawTag(raw_uid="tag--1", normalization=NormalizationMode.raw),
            RawTag(raw_uid="tag-2", normalization=NormalizationMode.raw),
            RawTag(raw_uid="taG-3", normalization=NormalizationMode.raw),
            RawTag(raw_uid="tag-4", normalization=NormalizationMode.raw),
            RawTag(raw_uid="tag--5", normalization=NormalizationMode.raw),
        ]

        expected = [
            NormalizedTag(uid=TagUid("tag-1"), link=None, categories=set()),
            NormalizedTag(uid=TagUid("tag-2"), link=None, categories=set()),
            NormalizedTag(uid=TagUid("tag-3"), link=None, categories=set()),
            NormalizedTag(uid=TagUid("tag-4"), link=None, categories=set()),
            NormalizedTag(uid=TagUid("tag-5"), link=None, categories=set()),
        ]

        resulted = await normalize(input)
        resulted.sort(key=lambda t: t.uid)

        expected.sort(key=lambda t: t.uid)

        assert resulted == expected

    @pytest.mark.asyncio
    async def test_copy_properties(self) -> None:
        input = [
            RawTag(
                raw_uid="tag-1",
                normalization=NormalizationMode.raw,
                link="http://example.com/tag1",
                categories={TagCategory.network_domain},
            ),
            RawTag(
                raw_uid="tag-2",
                normalization=NormalizationMode.raw,
                link="http://example.com/tag2",
                categories={TagCategory.feed_tag},
            ),
        ]

        expected = [
            NormalizedTag(
                uid=TagUid("tag-1"),
                link="http://example.com/tag1",
                categories={TagCategory.network_domain},
            ),
            NormalizedTag(
                uid=TagUid("tag-2"),
                link="http://example.com/tag2",
                categories={TagCategory.feed_tag},
            ),
        ]

        resulted = await normalize(input)
        resulted.sort(key=lambda t: t.uid)

        expected.sort(key=lambda t: t.uid)

        assert resulted == expected

    @pytest.mark.asyncio
    async def test_remove_duplicates(self) -> None:
        input = [
            RawTag(raw_uid="tag-1", normalization=NormalizationMode.raw),
            RawTag(raw_uid="tag-1", normalization=NormalizationMode.raw),
            RawTag(raw_uid="tag-2", normalization=NormalizationMode.raw),
            RawTag(raw_uid="tag-3", normalization=NormalizationMode.raw),
            RawTag(raw_uid="tag-2", normalization=NormalizationMode.raw),
        ]

        expected = [
            NormalizedTag(uid=TagUid("tag-1"), link=None, categories=set()),
            NormalizedTag(uid=TagUid("tag-2"), link=None, categories=set()),
            NormalizedTag(uid=TagUid("tag-3"), link=None, categories=set()),
        ]

        resulted = await normalize(input)
        resulted.sort(key=lambda t: t.uid)

        expected.sort(key=lambda t: t.uid)

        assert resulted == expected

    @pytest.mark.asyncio
    async def test_no_normalizers(self) -> None:
        input = [
            RawTag(raw_uid="tag--1", normalization=NormalizationMode.raw),
            RawTag(raw_uid="tag-2", normalization=NormalizationMode.raw),
            RawTag(raw_uid="tag-3--", normalization=NormalizationMode.raw),
        ]

        expected = [
            NormalizedTag(uid=TagUid("tag-1"), link=None, categories=set()),
            NormalizedTag(uid=TagUid("tag-2"), link=None, categories=set()),
            NormalizedTag(uid=TagUid("tag-3"), link=None, categories=set()),
        ]

        resulted = await normalize(input, normalizers_=[])
        resulted.sort(key=lambda t: t.uid)

        expected.sort(key=lambda t: t.uid)

        assert resulted == expected

    @pytest.mark.asyncio
    async def test_tags_chain(self, mocker: MockerFixture) -> None:  # pylint: disable=R0914
        tag_1 = RawTag(raw_uid="tag-1", normalization=NormalizationMode.preserve, link=None, categories=set())
        tag_2 = RawTag(raw_uid="tag-2", normalization=NormalizationMode.raw, link=None, categories=set())
        tag_3 = RawTag(raw_uid="tag-3", normalization=NormalizationMode.preserve, link=None, categories=set())

        tag_4 = tag_1.replace(raw_uid="tag-4", normalization=NormalizationMode.raw)
        tag_5 = tag_2.replace(raw_uid="tag-5", normalization=NormalizationMode.preserve)
        tag_6 = tag_3.replace(raw_uid="tag-6", normalization=NormalizationMode.raw)

        tag_7 = tag_1.replace(raw_uid="tag-7", normalization=NormalizationMode.preserve)
        tag_8 = tag_2.replace(raw_uid="tag-8", normalization=NormalizationMode.preserve)
        tag_9 = tag_3.replace(raw_uid="tag-9", normalization=NormalizationMode.preserve)

        tag_10 = tag_3.replace(raw_uid="tag-10", normalization=NormalizationMode.preserve)

        # Test:
        # - chains
        # - preserve
        # - duplication
        tag_map = {
            tag_1.raw_uid: [tag_4, tag_7],
            tag_2.raw_uid: [tag_5, tag_8, tag_1],
            tag_3.raw_uid: [tag_6, tag_9],
            tag_4.raw_uid: [tag_10],
            tag_5.raw_uid: [tag_2, tag_3, tag_10],
            tag_6.raw_uid: [tag_6],
            tag_9.raw_uid: [tag_9],
        }

        async def mocked_apply_normalizers(
            _normalizers: list[NormalizerInfo], tag_: TagInNormalization
        ) -> tuple[bool, list[RawTag]]:
            # we use `preserve` here just for simplicity of the map
            # to not add additional parameters
            if tag_.uid in tag_map:
                return (tag_.mode == NormalizationMode.preserve), tag_map[tag_.uid]
            return (tag_.mode == NormalizationMode.preserve), []

        mocker.patch("ffun.tags.domain.apply_normalizers", side_effect=mocked_apply_normalizers)

        resulted = await normalize([tag_1, tag_2, tag_3])
        resulted.sort(key=lambda t: t.uid)

        expected = [
            NormalizedTag(uid=TagUid("tag-1"), link=None, categories=set()),
            # tag-2 is not preserved
            NormalizedTag(uid=TagUid("tag-3"), link=None, categories=set()),
            # tag-4 is not preserved
            NormalizedTag(uid=TagUid("tag-5"), link=None, categories=set()),
            # tag-6 & tag-9 are produced simultaneously, but tag-6 is not preserved
            NormalizedTag(uid=TagUid("tag-7"), link=None, categories=set()),
            NormalizedTag(uid=TagUid("tag-8"), link=None, categories=set()),
            NormalizedTag(uid=TagUid("tag-9"), link=None, categories=set()),
            NormalizedTag(uid=TagUid("tag-10"), link=None, categories=set()),
        ]

        expected.sort(key=lambda t: t.uid)

        assert resulted == expected
