import contextlib
from typing import Generator

import pytest
from pytest_mock import MockerFixture

from ffun.core import metrics
from ffun.domain.entities import TagUid
from ffun.ontology.entities import NormalizationMode, RawTag
from ffun.tags import utils
from ffun.tags.entities import TagCategory, TagInNormalization
from ffun.tags.normalizers.base import FakeNormalizer, NormalizerAlwaysError, NormalizerInfo


@contextlib.contextmanager
def check_metric_accumulator(
    metric: metrics.Accumulator, count_delta: int, sum_delta: int
) -> Generator[None, None, None]:

    old_count = metric.count
    old_sum = metric.sum

    yield

    assert metric.count == old_count + count_delta
    assert metric.sum == old_sum + sum_delta


@contextlib.contextmanager
def check_metric_accumulators(
    mocker: MockerFixture, info: NormalizerInfo, measured: int, processed: int, consumed: int, produced: int
) -> Generator[None, None, None]:

    called_for = []

    def patch_flush(self: metrics.Accumulator) -> None:
        called_for.append(self)

    mocker.patch("ffun.core.metrics.Accumulator.flush_if_time", patch_flush)

    with (
        check_metric_accumulator(info.metric_processed, measured, processed),
        check_metric_accumulator(info.metric_consumed, measured, consumed),
        check_metric_accumulator(info.metric_produced, measured, produced),
    ):
        yield

    assert len(called_for) == 3

    assert info.metric_processed in called_for
    assert info.metric_consumed in called_for
    assert info.metric_produced in called_for


class TestNormalizerInfo:

    @pytest.fixture
    def tag(self) -> TagInNormalization:
        uid: TagUid = TagUid("example-tag")
        return TagInNormalization(
            uid=uid,
            parts=utils.uid_to_parts(uid),
            mode=NormalizationMode.preserve,
            link=None,
            categories={TagCategory.feed_tag},
        )

    @pytest.fixture
    def raw_tag_1(self) -> RawTag:
        return RawTag(
            raw_uid="new-tag-1",
            normalization=NormalizationMode.raw,
            link=None,
            categories={TagCategory.feed_tag},
        )

    @pytest.fixture
    def raw_tag_2(self) -> RawTag:
        return RawTag(
            raw_uid="new-tag-2",
            normalization=NormalizationMode.raw,
            link=None,
            categories={TagCategory.feed_tag},
        )

    @pytest.fixture
    def raw_tags(self, raw_tag_1: RawTag, raw_tag_2: RawTag) -> list[RawTag]:
        return [raw_tag_1, raw_tag_2]

    @pytest.mark.parametrize("tag_valid", [True, False])
    @pytest.mark.asyncio
    async def test_normalize__ok(
        self, tag_valid: bool, tag: TagInNormalization, raw_tags: list[RawTag], mocker: MockerFixture
    ) -> None:
        normalizer = FakeNormalizer(tag_valid, raw_tags)
        info = NormalizerInfo(id=1, name="fake", normalizer=normalizer)

        with check_metric_accumulators(
            mocker, info, measured=1, processed=1, consumed=0 if tag_valid else 1, produced=len(raw_tags)
        ):
            result_tag_valid, new_tags = await info.normalize(tag)

        assert result_tag_valid == tag_valid
        assert new_tags == raw_tags

    @pytest.mark.asyncio
    async def test_normalize__error(self, tag: TagInNormalization, mocker: MockerFixture) -> None:
        class FakeException(BaseException):
            pass

        normalizer = NormalizerAlwaysError(FakeException("test error"))
        info = NormalizerInfo(id=1, name="fake", normalizer=normalizer)

        with check_metric_accumulators(mocker, info, measured=0, processed=0, consumed=0, produced=0):
            result_tag_valid, new_tags = await info.normalize(tag)

        assert result_tag_valid
        assert new_tags == []
