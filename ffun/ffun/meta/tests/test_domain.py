import uuid
from itertools import chain

import pytest

from ffun.domain.domain import new_feed_id
from ffun.domain.urls import url_to_source_uid
from ffun.feeds import domain as f_domain
from ffun.feeds.entities import Feed
from ffun.feeds_links import domain as fl_domain
from ffun.library import domain as l_domain
from ffun.library.tests import make as l_make
from ffun.meta.domain import add_feeds, limit_entries_for_feed, remove_entries
from ffun.ontology import domain as o_domain
from ffun.ontology.entities import ProcessorTag
from ffun.parsers import entities as p_entities


class TestRemoveEntries:
    @pytest.mark.asyncio
    async def test_no_entries(self) -> None:
        await remove_entries([])

    @pytest.mark.asyncio
    async def test_success(
        self,
        loaded_feed: Feed,
        another_loaded_feed: Feed,
        fake_processor_id: int,
        another_fake_processor_id: int,
        three_processor_tags: tuple[ProcessorTag, ProcessorTag, ProcessorTag],
    ) -> None:
        entries = await l_make.n_entries_list(loaded_feed, 3)
        another_entries = await l_make.n_entries_list(another_loaded_feed, 3)

        tag_a, tag_b, tag_c = three_processor_tags

        # fill feed 1
        await o_domain.apply_tags_to_entry(entry_id=entries[0].id, processor_id=fake_processor_id, tags=[tag_a])

        await o_domain.apply_tags_to_entry(entry_id=entries[1].id, processor_id=fake_processor_id, tags=[tag_a])

        await o_domain.apply_tags_to_entry(
            entry_id=entries[1].id, processor_id=another_fake_processor_id, tags=[tag_b]
        )

        # fill feed 2
        await o_domain.apply_tags_to_entry(
            entry_id=another_entries[1].id, processor_id=fake_processor_id, tags=[tag_a]
        )

        await o_domain.apply_tags_to_entry(
            entry_id=another_entries[1].id, processor_id=another_fake_processor_id, tags=[tag_b]
        )

        await o_domain.apply_tags_to_entry(
            entry_id=another_entries[2].id, processor_id=another_fake_processor_id, tags=[tag_c]
        )

        await remove_entries([entries[0].id, another_entries[1].id, entries[2].id])

        loaded_entries = await l_domain.get_entries_by_ids(
            [entry.id for entry in entries] + [entry.id for entry in another_entries]
        )

        assert loaded_entries == {
            entries[0].id: None,
            entries[1].id: entries[1],
            entries[2].id: None,
            another_entries[0].id: another_entries[0],
            another_entries[1].id: None,
            another_entries[2].id: another_entries[2],
        }


class TestLimitEntriesForFeed:
    @pytest.mark.xfail
    @pytest.mark.asyncio
    async def test_no_feed(self) -> None:
        await limit_entries_for_feed(new_feed_id(), limit=10)

    @pytest.mark.xfail
    @pytest.mark.asyncio
    async def test_no_entries(self, loaded_feed: Feed) -> None:
        await limit_entries_for_feed(loaded_feed.id, limit=10)

    @pytest.mark.xfail
    @pytest.mark.asyncio
    async def test_not_exceed_limit(self, loaded_feed: Feed) -> None:
        entries = await l_make.n_entries_list(loaded_feed, 3)

        await limit_entries_for_feed(loaded_feed.id, limit=10)

        loaded_entries = await l_domain.get_entries_by_filter(feeds_ids=[loaded_feed.id], limit=100)

        assert loaded_entries == entries

    @pytest.mark.xfail
    @pytest.mark.asyncio
    async def test_exceed_limit(self, loaded_feed: Feed) -> None:
        entries = await l_make.n_entries_list(loaded_feed, 10)

        await limit_entries_for_feed(loaded_feed.id, limit=5)

        loaded_entries = await l_domain.get_entries_by_filter(feeds_ids=[loaded_feed.id], limit=100)

        assert loaded_entries == entries[:5]


class TestAddFeeds:

    @pytest.mark.asyncio
    async def test_no_feeds_to_add(self, internal_user_id: uuid.UUID) -> None:
        await add_feeds([], internal_user_id)

    @pytest.mark.asyncio
    async def test_add(self, internal_user_id: uuid.UUID, another_internal_user_id: uuid.UUID) -> None:

        feeds = [
            p_entities.FeedInfo(
                url=f"{uuid.uuid4().hex}.com", title=uuid.uuid4().hex, description=uuid.uuid4().hex, entries=[]
            ),
            p_entities.FeedInfo(
                url=f"{uuid.uuid4().hex}.com", title=uuid.uuid4().hex, description=uuid.uuid4().hex, entries=[]
            ),
            p_entities.FeedInfo(
                url=f"{uuid.uuid4().hex}.com", title=uuid.uuid4().hex, description=uuid.uuid4().hex, entries=[]
            ),
        ]

        await add_feeds(feeds[:2], internal_user_id)
        await add_feeds(feeds[1:], another_internal_user_id)

        links_1 = await fl_domain.get_linked_feeds(internal_user_id)
        links_2 = await fl_domain.get_linked_feeds(another_internal_user_id)

        feeds_1 = await f_domain.get_feeds([link.feed_id for link in links_1])
        feeds_2 = await f_domain.get_feeds([link.feed_id for link in links_2])

        assert len({feed.id for feed in feeds_1} & {feed.id for feed in feeds_2}) == 1

        assert {feed.url for feed in feeds_1} == {feed.url for feed in feeds[:2]}
        assert {feed.url for feed in feeds_2} == {feed.url for feed in feeds[1:]}

        urls = {feed.url for feed in feeds}

        source_uids = {url: url_to_source_uid(url) for url in urls}
        source_ids = await f_domain.get_source_ids(source_uids.values())

        for feed in chain(feeds_1, feeds_2):
            assert feed.source_id == source_ids[source_uids[feed.url]]
