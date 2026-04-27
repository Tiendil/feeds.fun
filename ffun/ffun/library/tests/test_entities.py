import datetime

import pytest

from ffun.core import utils
from ffun.domain.urls import str_to_absolute_url
from ffun.library import errors
from ffun.library.entities import (
    REFERENCE_KIND_PRIORITY,
    CollectedEntry,
    Entry,
    Reference,
    ReferenceKind,
)


class TestEntry:
    @pytest.mark.parametrize(
        ("published_at", "created_at", "expected_published_at"),
        [
            (
                datetime.datetime(2026, 1, 2, 3, 4, 4, tzinfo=datetime.UTC),
                datetime.datetime(2026, 1, 2, 3, 4, 5, tzinfo=datetime.UTC),
                datetime.datetime(2026, 1, 2, 3, 4, 4, tzinfo=datetime.UTC),
            ),
            (
                datetime.datetime.min.replace(tzinfo=datetime.UTC),
                datetime.datetime(2026, 1, 2, 3, 4, 5, tzinfo=datetime.UTC),
                datetime.datetime(2026, 1, 2, 3, 4, 5, tzinfo=datetime.UTC),
            ),
            (
                utils.zero_timestamp(),
                datetime.datetime(2026, 1, 2, 3, 4, 5, tzinfo=datetime.UTC),
                datetime.datetime(2026, 1, 2, 3, 4, 5, tzinfo=datetime.UTC),
            ),
            (
                datetime.datetime(2026, 1, 2, 3, 4, 6, tzinfo=datetime.UTC),
                datetime.datetime(2026, 1, 2, 3, 4, 5, tzinfo=datetime.UTC),
                datetime.datetime(2026, 1, 2, 3, 4, 5, tzinfo=datetime.UTC),
            ),
        ],
    )
    def test_published_at_for_processing(
        self,
        new_entry: CollectedEntry,
        published_at: datetime.datetime,
        created_at: datetime.datetime,
        expected_published_at: datetime.datetime,
    ) -> None:
        entry = new_entry.replace(published_at=published_at).fake_entry(created_at)

        assert entry.published_at_for_processing == expected_published_at

    def test_published_at_for_processing__asserts_timezone_in_published_at(self, new_entry: CollectedEntry) -> None:
        created_at = datetime.datetime(2026, 1, 2, 3, 4, 5, tzinfo=datetime.UTC)
        entry = new_entry.replace(published_at=datetime.datetime(2026, 1, 2, 3, 4, 4)).fake_entry(created_at)

        with pytest.raises(AssertionError):
            _ = entry.published_at_for_processing

    def test_published_at_for_processing__asserts_timezone_in_created_at(self, new_entry: CollectedEntry) -> None:
        entry = new_entry.fake_entry(datetime.datetime(2026, 1, 2, 3, 4, 5))

        with pytest.raises(AssertionError):
            _ = entry.published_at_for_processing

    def test_age_for_processing(self, new_entry: CollectedEntry) -> None:
        created_at = datetime.datetime(2026, 1, 2, 3, 4, 5, tzinfo=datetime.UTC)
        entry = new_entry.replace(published_at=utils.zero_timestamp()).fake_entry(created_at)
        before = utils.now()
        age_for_processing = entry.age_for_processing
        after = utils.now()

        assert before - created_at <= age_for_processing <= after - created_at

    def test_collected_entry(self, new_entry: CollectedEntry) -> None:
        created_at = datetime.datetime(2026, 1, 2, 3, 4, 5, tzinfo=datetime.UTC)
        entry = new_entry.fake_entry(created_at)

        assert entry.collected_entry() == CollectedEntry(
            id=entry.id,
            source_id=entry.source_id,
            title=entry.title,
            body=entry.body,
            external_id=entry.external_id,
            external_url=entry.external_url,
            external_tags=entry.external_tags,
            published_at=entry.published_at,
            references=entry.references,
        )


class TestCollectedEntry:
    def test_fake_entry(self, new_entry: CollectedEntry) -> None:
        created_at = datetime.datetime(2026, 1, 2, 3, 4, 5, tzinfo=datetime.UTC)

        assert new_entry.fake_entry(created_at) == Entry(
            id=new_entry.id,
            source_id=new_entry.source_id,
            title=new_entry.title,
            body=new_entry.body,
            external_id=new_entry.external_id,
            external_url=new_entry.external_url,
            external_tags=new_entry.external_tags,
            published_at=new_entry.published_at,
            created_at=created_at,
            references=new_entry.references,
        )


class TestReferenceKindPriority:
    def test_is_not_changed(self) -> None:
        assert REFERENCE_KIND_PRIORITY == {
            ReferenceKind.unknown: 0,
            ReferenceKind.page: 1,
            ReferenceKind.document: 2,
            ReferenceKind.author: 4,
            ReferenceKind.comments: 3,
            ReferenceKind.audio: 3,
            ReferenceKind.video: 3,
            ReferenceKind.image: 3,
        }


class TestReference:
    def test_merge_raises_on_different_urls(self) -> None:
        reference_1 = Reference(kind=ReferenceKind.page, url=str_to_absolute_url("https://example.com/1"))
        reference_2 = Reference(kind=ReferenceKind.page, url=str_to_absolute_url("https://example.com/2"))

        with pytest.raises(errors.ReferenceUrlsMismatchOnMerge):
            reference_1.merge(reference_2)

    def test_merge_keeps_self_when_self_has_higher_or_equal_priority(self) -> None:
        reference_1 = Reference(
            kind=ReferenceKind.comments,
            url=str_to_absolute_url("https://example.com/reference"),
            title="title-1",
            mime_type="text/html",
            width=100,
            duration=datetime.timedelta(seconds=5),
            extra={"a": "b"},
        )
        reference_2 = Reference(
            kind=ReferenceKind.page,
            url=str_to_absolute_url("https://example.com/reference"),
            title="title-2",
            mime_type="application/pdf",
            height=200,
            size=42,
        )

        assert reference_1.merge(reference_2) == Reference(
            kind=ReferenceKind.comments,
            url=str_to_absolute_url("https://example.com/reference"),
            title="title-1",
            mime_type="text/html",
            width=100,
            height=200,
            duration=datetime.timedelta(seconds=5),
            size=42,
            extra={"a": "b"},
        )

    def test_merge_uses_other_when_other_has_higher_priority(self) -> None:
        reference_1 = Reference(
            kind=ReferenceKind.page,
            url=str_to_absolute_url("https://example.com/reference"),
            title=None,
            mime_type=None,
            width=None,
            height=200,
            duration=None,
            size=42,
            extra=None,
        )
        reference_2 = Reference(
            kind=ReferenceKind.video,
            url=str_to_absolute_url("https://example.com/reference"),
            title="video",
            mime_type="video/mp4",
            width=640,
            height=None,
            duration=datetime.timedelta(seconds=5),
            size=None,
            extra={"id": "123"},
        )

        assert reference_1.merge(reference_2) == Reference(
            kind=ReferenceKind.video,
            url=str_to_absolute_url("https://example.com/reference"),
            title="video",
            mime_type="video/mp4",
            width=640,
            height=200,
            duration=datetime.timedelta(seconds=5),
            size=42,
            extra={"id": "123"},
        )
