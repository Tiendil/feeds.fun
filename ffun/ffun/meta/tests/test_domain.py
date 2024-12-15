import uuid
from itertools import chain

import pytest
import pytest_asyncio

from ffun.core.postgresql import execute
from ffun.domain.entities import UserId
from ffun.domain.urls import str_to_feed_url, url_to_source_uid, url_to_uid
from ffun.feeds import domain as f_domain
from ffun.feeds.entities import Feed
from ffun.feeds_links import domain as fl_domain
from ffun.library import domain as l_domain
from ffun.library.tests import make as l_make
from ffun.meta.domain import add_feeds, clean_orphaned_entries, remove_entries
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


class TestAddFeeds:

    @pytest.mark.asyncio
    async def test_no_feeds_to_add(self, internal_user_id: UserId) -> None:
        await add_feeds([], internal_user_id)

    @pytest.mark.asyncio
    async def test_add(self, internal_user_id: UserId, another_internal_user_id: UserId) -> None:

        urls = [str_to_feed_url(f"{uuid.uuid4().hex}.com") for _ in range(3)]

        feeds = [
            p_entities.FeedInfo(
                url=urls[0],
                title=uuid.uuid4().hex,
                description=uuid.uuid4().hex,
                entries=[],
                uid=url_to_uid(urls[0]),
            ),
            p_entities.FeedInfo(
                url=urls[1],
                title=uuid.uuid4().hex,
                description=uuid.uuid4().hex,
                entries=[],
                uid=url_to_uid(urls[1]),
            ),
            p_entities.FeedInfo(
                url=urls[2], title=uuid.uuid4().hex, description=uuid.uuid4().hex, entries=[], uid=url_to_uid(urls[2])
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

        source_uids = {url: url_to_source_uid(url) for url in urls}
        source_ids = await f_domain.get_source_ids(source_uids.values())

        for feed in chain(feeds_1, feeds_2):
            assert feed.source_id == source_ids[source_uids[feed.url]]


# test that everything is connected correctly
# detailed cases are covered in tests of functioned called in clean_orphaned_entries
class TestCleanOrphanedEntries:

    @pytest_asyncio.fixture(autouse=True)
    async def cleanup_orphaned_entries(self) -> None:
        await execute("DELETE FROM l_orphaned_entries")

    @pytest.mark.asyncio
    async def test(self, loaded_feed: Feed) -> None:
        entries = await l_make.n_entries_list(loaded_feed, n=10)

        await l_domain.unlink_feed_tail(loaded_feed.id, offset=3)

        removed_1 = await clean_orphaned_entries(chunk=5)

        assert removed_1 == 5

        removed_2 = await clean_orphaned_entries(chunk=5)

        assert removed_2 == 2

        loaded_entries = await l_domain.get_entries_by_ids([entry.id for entry in entries])

        assert loaded_entries == {entry.id: entry for entry in entries[:3]} | {entry.id: None for entry in entries[3:]}
