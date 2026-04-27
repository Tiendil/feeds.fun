import datetime

from ffun.domain.domain import new_entry_id, new_source_id
from ffun.domain.urls import str_to_absolute_url
from ffun.library.entities import CollectedEntry, Reference, ReferenceKind
from ffun.parsers.entities import EntryInfo


class TestEntryInfo:
    def test_to_collected_entry(self) -> None:
        entry_info = EntryInfo(
            title="Entry title",
            body="Entry body",
            external_id="external-id",
            external_url=str_to_absolute_url("https://example.com/news"),
            external_tags={"tag-1", "tag-2"},
            published_at=datetime.datetime(2026, 4, 14, 10, 30, tzinfo=datetime.UTC),
            references=[
                Reference(
                    kind=ReferenceKind.video,
                    url=str_to_absolute_url("https://example.com/video"),
                    title="Video reference",
                    mime_type="video/mp4",
                ),
                Reference(
                    kind=ReferenceKind.comments,
                    url=str_to_absolute_url("https://example.com/comments"),
                    title="Comments",
                ),
            ],
        )
        entry_id = new_entry_id()
        source_id = new_source_id()

        assert entry_info.to_collected_entry(entry_id, source_id) == CollectedEntry(
            id=entry_id,
            source_id=source_id,
            title="Entry title",
            body="Entry body",
            external_id="external-id",
            external_url=str_to_absolute_url("https://example.com/news"),
            external_tags={"tag-1", "tag-2"},
            published_at=datetime.datetime(2026, 4, 14, 10, 30, tzinfo=datetime.UTC),
            references=[
                Reference(
                    kind=ReferenceKind.video,
                    url=str_to_absolute_url("https://example.com/video"),
                    title="Video reference",
                    mime_type="video/mp4",
                ),
                Reference(
                    kind=ReferenceKind.comments,
                    url=str_to_absolute_url("https://example.com/comments"),
                    title="Comments",
                ),
            ],
        )
