import datetime

import pytest

from ffun.core import utils
from ffun.library.entities import CollectedEntry, Entry


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
        )
