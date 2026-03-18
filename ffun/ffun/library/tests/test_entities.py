import datetime

from ffun.core import utils
from ffun.library.entities import CollectedEntry, Entry


class TestEntry:
    def test_global_age_uses_created_at(self, new_entry: CollectedEntry) -> None:
        created_at = datetime.datetime(2026, 1, 2, 3, 4, 5, tzinfo=datetime.UTC)
        entry = new_entry.fake_entry(created_at).replace(published_at=created_at - datetime.timedelta(days=7))
        before = utils.now()
        global_age = entry.global_age
        after = utils.now()

        assert before - created_at <= global_age <= after - created_at

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
