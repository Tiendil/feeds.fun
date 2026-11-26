import datetime

import pytest

from ffun.core.utils import now, zero_timestamp
from ffun.domain.entities import AbsoluteUrl, FeedUrl
from ffun.domain.urls import str_to_resource_url, url_to_uid
from ffun.extractors.domain import EntryBuilder, FeedBuilder
from ffun.parsers.entities import EntryInfo, FeedInfo

_FEED_URL = str_to_resource_url("https://news.example/articles")
_ENTRY_URL = AbsoluteUrl("https://news.example/articles/first")


class TestEntryBuilder:
    @pytest.fixture()
    def entry_builder(self) -> EntryBuilder:
        return EntryBuilder(_ENTRY_URL)

    @pytest.mark.parametrize("first", ["First title", ""])
    def test_add_title__keeps_the_first_value(self, entry_builder: EntryBuilder, first: str) -> None:
        entry_builder.add_title(first)
        entry_builder.add_title("Later title")

        entry = entry_builder.build()

        assert entry is not None
        assert entry.title == first

    @pytest.mark.parametrize("first", ["First body", ""])
    def test_add_body__keeps_the_first_value_received_before_the_title(
        self, entry_builder: EntryBuilder, first: str
    ) -> None:
        entry_builder.add_body(first)
        entry_builder.add_body("Later body")
        entry_builder.add_title("First title")

        entry = entry_builder.build()

        assert entry is not None
        assert entry.body == first

    def test_add_published_at__keeps_the_first_date_received_before_the_title(
        self, entry_builder: EntryBuilder
    ) -> None:
        first = now()
        entry_builder.add_published_at(first)
        entry_builder.add_published_at(first + datetime.timedelta(days=1))
        entry_builder.add_title("First title")

        entry = entry_builder.build()

        assert entry is not None
        assert entry.published_at == first

    def test_add_published_at__rejects_a_naive_datetime(self, entry_builder: EntryBuilder) -> None:
        naive_date = now().replace(tzinfo=None)

        with pytest.raises(ValueError, match="must include a timezone"):
            entry_builder.add_published_at(naive_date)

        assert entry_builder.published_at is None

    def test_published_at__is_unset_before_assignment(self, entry_builder: EntryBuilder) -> None:
        assert entry_builder.published_at is None

    def test_published_at__reports_the_assigned_value(self, entry_builder: EntryBuilder) -> None:
        published_at = now()

        entry_builder.add_published_at(published_at)

        assert entry_builder.published_at == published_at

    def test_build__omits_a_draft_without_a_title(self, entry_builder: EntryBuilder) -> None:
        entry_builder.add_body("Story preview")
        entry_builder.add_published_at(now())

        assert entry_builder.build() is None

    def test_build__fills_defaults_for_a_title_only_entry(self, entry_builder: EntryBuilder) -> None:
        entry_builder.add_title("City news")

        assert entry_builder.build() == EntryInfo(
            title="City news",
            body="",
            external_id=_ENTRY_URL,
            external_url=_ENTRY_URL,
            external_tags=set(),
            published_at=zero_timestamp(),
            references=[],
        )

    def test_build__preserves_the_supplied_body(self, entry_builder: EntryBuilder) -> None:
        entry_builder.add_title("City news")
        entry_builder.add_body("Story preview")

        entry = entry_builder.build()

        assert entry is not None
        assert entry.body == "Story preview"

    def test_build__preserves_the_supplied_publication_time(self, entry_builder: EntryBuilder) -> None:
        published_at = now()
        entry_builder.add_title("City news")
        entry_builder.add_published_at(published_at)

        entry = entry_builder.build()

        assert entry is not None
        assert entry.published_at == published_at


class TestFeedBuilder:
    @pytest.fixture()
    def builder(self) -> FeedBuilder:
        return FeedBuilder(_FEED_URL)

    @pytest.mark.parametrize("first", ["City news", ""])
    def test_add_title__keeps_the_first_value(self, builder: FeedBuilder, first: str) -> None:
        builder.add_title(first)
        builder.add_title("Later title")

        assert builder.build().title == first

    @pytest.mark.parametrize("first", ["Weekly reports", ""])
    def test_add_description__keeps_the_first_value(self, builder: FeedBuilder, first: str) -> None:
        builder.add_description(first)
        builder.add_description("Later description")

        assert builder.build().description == first

    def test_add_site_url__keeps_the_first_value(self, builder: FeedBuilder) -> None:
        first = AbsoluteUrl("https://news.example/home")
        builder.add_site_url(first)
        builder.add_site_url(AbsoluteUrl("https://news.example/other"))

        assert builder.build().site_url == first

    def test_get_or_create__returns_the_same_builder_for_a_url(self, builder: FeedBuilder) -> None:
        entry_builder = builder.get_or_create(_ENTRY_URL)

        assert builder.get_or_create(_ENTRY_URL) is entry_builder

    def test_get_or_create__returns_distinct_builders_for_different_urls(self, builder: FeedBuilder) -> None:
        first = builder.get_or_create(_ENTRY_URL)
        second = builder.get_or_create(AbsoluteUrl("https://news.example/articles/second"))

        assert first is not second

    def test_build__returns_an_empty_feed_with_default_metadata(self, builder: FeedBuilder) -> None:
        assert builder.build() == FeedInfo(
            url=FeedUrl(_FEED_URL), uid=url_to_uid(_FEED_URL), title="", description="", site_url=None, entries=[]
        )

    def test_build__preserves_an_untitled_draft_for_a_later_title(self, builder: FeedBuilder) -> None:
        entry_builder = builder.get_or_create(_ENTRY_URL)
        entry_builder.add_body("Story preview")

        assert builder.build().entries == []

        entry_builder.add_title("First title")
        (entry,) = builder.build().entries

        assert entry.body == "Story preview"

    def test_build__sorts_dated_entries_newest_first(self, builder: FeedBuilder) -> None:
        earlier = AbsoluteUrl("https://news.example/articles/earlier")
        newer = AbsoluteUrl("https://news.example/articles/newer")
        newer_date = now()
        earlier_entry = builder.get_or_create(earlier)
        earlier_entry.add_title("Earlier")
        earlier_entry.add_published_at(newer_date - datetime.timedelta(days=1))
        newer_entry = builder.get_or_create(newer)
        newer_entry.add_title("Newer")
        newer_entry.add_published_at(newer_date)

        assert [entry.external_url for entry in builder.build().entries] == [newer, earlier]

    def test_build__places_undated_entries_after_pre_epoch_dated_entries(self, builder: FeedBuilder) -> None:
        earlier = AbsoluteUrl("https://news.example/articles/earlier")
        builder.get_or_create(_ENTRY_URL).add_title("Undated")
        earlier_entry = builder.get_or_create(earlier)
        earlier_entry.add_title("Earlier")
        earlier_entry.add_published_at(zero_timestamp() - datetime.timedelta(days=1))

        assert [entry.external_url for entry in builder.build().entries] == [earlier, _ENTRY_URL]
