import uuid
from itertools import chain

import pytest

from ffun.feeds import domain as f_domain
from ffun.feeds import errors as f_errors
from ffun.feeds_links import domain as fl_domain
from ffun.library import domain as l_domain
from ffun.library.tests import make as l_make
from ffun.markers import domain as m_domains
from ffun.markers.entities import Marker
from ffun.meta.domain import limit_entries_for_feed, merge_feeds, remove_entries, remove_feed
from ffun.ontology import domain as o_domain
from ffun.ontology.entities import ProcessorTag
from ffun.users.tests import make as u_make


class TestRemoveFeed:
    @pytest.mark.asyncio
    async def test_no_feed(self) -> None:
        await remove_feed(uuid.uuid4())

    @pytest.mark.asyncio
    async def test_success(
        self,
        loaded_feed_id: uuid.UUID,
        another_loaded_feed_id: uuid.UUID,
        fake_processor_id: int,
        another_fake_processor_id: int,
        three_processor_tags: tuple[ProcessorTag, ProcessorTag, ProcessorTag],
    ) -> None:
        entries = await l_make.n_entries_list(loaded_feed_id, 3)
        another_entries = await l_make.n_entries_list(another_loaded_feed_id, 3)

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

        await remove_feed(loaded_feed_id)

        loaded_entries = await l_domain.get_entries_by_ids(
            [entry.id for entry in entries] + [entry.id for entry in another_entries]
        )

        assert loaded_entries == {
            entries[0].id: None,
            entries[1].id: None,
            entries[2].id: None,
            another_entries[0].id: another_entries[0],
            another_entries[1].id: another_entries[1],
            another_entries[2].id: another_entries[2],
        }

    @pytest.mark.asyncio
    async def test_remove_markers(self, loaded_feed_id: uuid.UUID, another_loaded_feed_id: uuid.UUID) -> None:
        entries = await l_make.n_entries_list(loaded_feed_id, 3)

        another_entries = await l_make.n_entries_list(another_loaded_feed_id, 3)

        user_a, user_b, user_c = await u_make.n_users(3)

        await m_domains.set_marker(user_a, Marker.read, entries[0].id)
        await m_domains.set_marker(user_b, Marker.read, entries[1].id)
        await m_domains.set_marker(user_b, Marker.read, entries[2].id)

        await m_domains.set_marker(user_b, Marker.read, another_entries[0].id)
        await m_domains.set_marker(user_c, Marker.read, another_entries[1].id)
        await m_domains.set_marker(user_c, Marker.read, another_entries[2].id)

        await remove_feed(loaded_feed_id)

        markers_a = await m_domains.get_markers(user_a, [entry.id for entry in chain(entries, another_entries)])
        markers_b = await m_domains.get_markers(user_b, [entry.id for entry in chain(entries, another_entries)])
        markers_c = await m_domains.get_markers(user_c, [entry.id for entry in chain(entries, another_entries)])

        assert markers_a == {}
        assert markers_b == {another_entries[0].id: {Marker.read}}
        assert markers_c == {another_entries[1].id: {Marker.read}, another_entries[2].id: {Marker.read}}


class TestMergeFeeds:
    @pytest.mark.asyncio
    async def test_no_entries_in_source_feed(
        self, loaded_feed_id: uuid.UUID, another_loaded_feed_id: uuid.UUID
    ) -> None:
        await merge_feeds(loaded_feed_id, another_loaded_feed_id)

    @pytest.mark.asyncio
    async def test_move_entries_to_an_empty_feed(
        self,
        loaded_feed_id: uuid.UUID,
        another_loaded_feed_id: uuid.UUID,
        fake_processor_id: int,
        another_fake_processor_id: int,
        three_processor_tags: tuple[ProcessorTag, ProcessorTag, ProcessorTag],
    ) -> None:
        entries = await l_make.n_entries_list(loaded_feed_id, 3)

        tag_a, tag_b, tag_c = three_processor_tags

        await o_domain.apply_tags_to_entry(entry_id=entries[0].id, processor_id=fake_processor_id, tags=[tag_a])

        await o_domain.apply_tags_to_entry(entry_id=entries[1].id, processor_id=fake_processor_id, tags=[tag_a])

        await o_domain.apply_tags_to_entry(
            entry_id=entries[1].id, processor_id=another_fake_processor_id, tags=[tag_b]
        )

        await merge_feeds(another_loaded_feed_id, loaded_feed_id)

        with pytest.raises(f_errors.NoFeedFound):
            await f_domain.get_feed(loaded_feed_id)

        loaded_entries = await l_domain.get_entries_by_filter(feeds_ids=[another_loaded_feed_id], limit=100)

        assert loaded_entries == [entry.replace(feed_id=another_loaded_feed_id) for entry in entries]

        tags = await o_domain.get_tags_for_entries([entry.id for entry in loaded_entries])

        assert tags == {
            entries[0].id: {tag_a.raw_uid},
            entries[1].id: {tag_a.raw_uid, tag_b.raw_uid},
            entries[2].id: set(),
        }

    @pytest.mark.asyncio
    async def test_merge_entries(
        self,
        loaded_feed_id: uuid.UUID,
        another_loaded_feed_id: uuid.UUID,
        fake_processor_id: int,
        another_fake_processor_id: int,
        three_processor_tags: tuple[ProcessorTag, ProcessorTag, ProcessorTag],
    ) -> None:
        entries = await l_make.n_entries_list(loaded_feed_id, 3)

        another_entries_to_save = [entry.replace(feed_id=another_loaded_feed_id, id=uuid.uuid4()) for entry in entries]
        await l_domain.catalog_entries(reversed(another_entries_to_save))

        another_entries = await l_domain.get_entries_by_filter(feeds_ids=[another_loaded_feed_id], limit=100)

        tag_a, tag_b, tag_c = three_processor_tags

        # fill feed 1
        await o_domain.apply_tags_to_entry(entry_id=entries[0].id, processor_id=fake_processor_id, tags=[tag_a])

        await o_domain.apply_tags_to_entry(entry_id=entries[1].id, processor_id=fake_processor_id, tags=[tag_a])

        await o_domain.apply_tags_to_entry(
            entry_id=entries[1].id, processor_id=another_fake_processor_id, tags=[tag_b]
        )

        # fill feed 2
        await o_domain.apply_tags_to_entry(
            entry_id=another_entries[1].id, processor_id=fake_processor_id, tags=[tag_c]
        )

        await o_domain.apply_tags_to_entry(
            entry_id=another_entries[1].id, processor_id=another_fake_processor_id, tags=[tag_b]
        )

        await o_domain.apply_tags_to_entry(
            entry_id=another_entries[2].id, processor_id=another_fake_processor_id, tags=[tag_c]
        )

        await merge_feeds(another_loaded_feed_id, loaded_feed_id)

        with pytest.raises(f_errors.NoFeedFound):
            await f_domain.get_feed(loaded_feed_id)

        loaded_entries = await l_domain.get_entries_by_filter(feeds_ids=[another_loaded_feed_id], limit=100)

        assert loaded_entries == another_entries
        assert loaded_entries == [
            entry.replace(
                feed_id=another_loaded_feed_id, id=another_entries[i].id, cataloged_at=another_entries[i].cataloged_at
            )
            for i, entry in enumerate(entries)
        ]

        tags = await o_domain.get_tags_for_entries([entry.id for entry in loaded_entries])

        assert tags == {
            another_entries[0].id: {tag_a.raw_uid},
            another_entries[1].id: {tag_a.raw_uid, tag_b.raw_uid, tag_c.raw_uid},
            another_entries[2].id: {tag_c.raw_uid},
        }

    @pytest.mark.asyncio
    async def test_move_and_merge(
        self,
        loaded_feed_id: uuid.UUID,
        another_loaded_feed_id: uuid.UUID,
        fake_processor_id: int,
        another_fake_processor_id: int,
        three_processor_tags: tuple[ProcessorTag, ProcessorTag, ProcessorTag],
    ) -> None:
        entries = await l_make.n_entries_list(loaded_feed_id, 3)

        another_entries_to_save = [
            entry.replace(feed_id=another_loaded_feed_id, id=uuid.uuid4()) for entry in entries[1:]
        ]
        await l_domain.catalog_entries(reversed(another_entries_to_save))

        another_entries = await l_domain.get_entries_by_filter(feeds_ids=[another_loaded_feed_id], limit=100)

        tag_a, tag_b, tag_c = three_processor_tags

        # fill feed 1
        await o_domain.apply_tags_to_entry(entry_id=entries[0].id, processor_id=fake_processor_id, tags=[tag_a])

        await o_domain.apply_tags_to_entry(entry_id=entries[1].id, processor_id=fake_processor_id, tags=[tag_a])

        await o_domain.apply_tags_to_entry(
            entry_id=entries[1].id, processor_id=another_fake_processor_id, tags=[tag_b]
        )

        # fill feed 2
        await o_domain.apply_tags_to_entry(
            entry_id=another_entries[0].id, processor_id=fake_processor_id, tags=[tag_c]
        )

        await o_domain.apply_tags_to_entry(
            entry_id=another_entries[0].id, processor_id=another_fake_processor_id, tags=[tag_b]
        )

        await o_domain.apply_tags_to_entry(
            entry_id=another_entries[1].id, processor_id=another_fake_processor_id, tags=[tag_c]
        )

        await merge_feeds(another_loaded_feed_id, loaded_feed_id)

        with pytest.raises(f_errors.NoFeedFound):
            await f_domain.get_feed(loaded_feed_id)

        loaded_entries = await l_domain.get_entries_by_filter(feeds_ids=[another_loaded_feed_id], limit=100)

        assert loaded_entries[-1] == entries[0].replace(feed_id=another_loaded_feed_id)
        assert loaded_entries[:-1] == another_entries

        tags = await o_domain.get_tags_for_entries([entry.id for entry in loaded_entries])

        assert tags == {
            entries[0].id: {tag_a.raw_uid},
            another_entries[0].id: {tag_a.raw_uid, tag_b.raw_uid, tag_c.raw_uid},
            another_entries[1].id: {tag_c.raw_uid},
        }

    @pytest.mark.asyncio
    async def test_merge_feed_links(self, loaded_feed_id: uuid.UUID, another_loaded_feed_id: uuid.UUID) -> None:
        user_a, user_b = await u_make.n_users(2)

        await fl_domain.add_link(user_a, another_loaded_feed_id)
        await fl_domain.add_link(user_b, loaded_feed_id)
        await fl_domain.add_link(user_b, another_loaded_feed_id)

        await merge_feeds(loaded_feed_id, another_loaded_feed_id)

        links_a = await fl_domain.get_linked_feeds(user_a)
        links_b = await fl_domain.get_linked_feeds(user_b)

        assert {link.feed_id for link in links_a} == {loaded_feed_id}
        assert {link.feed_id for link in links_b} == {loaded_feed_id}

    @pytest.mark.asyncio
    async def test_merge_markers(self, loaded_feed_id: uuid.UUID, another_loaded_feed_id: uuid.UUID) -> None:
        entries = await l_make.n_entries_list(loaded_feed_id, 3)

        another_entries_to_save = [entry.replace(feed_id=another_loaded_feed_id, id=uuid.uuid4()) for entry in entries]
        await l_domain.catalog_entries(reversed(another_entries_to_save))

        another_entries = await l_domain.get_entries_by_filter(feeds_ids=[another_loaded_feed_id], limit=100)

        user_a, user_b, user_c = await u_make.n_users(3)

        await m_domains.set_marker(user_a, Marker.read, another_entries[1].id)
        await m_domains.set_marker(user_b, Marker.read, entries[0].id)
        await m_domains.set_marker(user_b, Marker.read, another_entries[0].id)
        await m_domains.set_marker(user_b, Marker.read, entries[2].id)
        await m_domains.set_marker(user_c, Marker.read, entries[1].id)

        await merge_feeds(another_loaded_feed_id, loaded_feed_id)

        markers_a = await m_domains.get_markers(user_a, [entry.id for entry in another_entries])
        markers_b = await m_domains.get_markers(user_b, [entry.id for entry in another_entries])
        markers_c = await m_domains.get_markers(user_c, [entry.id for entry in another_entries])

        assert markers_a == {another_entries[1].id: {Marker.read}}
        assert markers_b == {another_entries[0].id: {Marker.read}, another_entries[2].id: {Marker.read}}
        assert markers_c == {another_entries[1].id: {Marker.read}}


class TestRemoveEntries:
    @pytest.mark.asyncio
    async def test_no_entries(self) -> None:
        await remove_entries([])

    @pytest.mark.asyncio
    async def test_success(
        self,
        loaded_feed_id: uuid.UUID,
        another_loaded_feed_id: uuid.UUID,
        fake_processor_id: int,
        another_fake_processor_id: int,
        three_processor_tags: tuple[ProcessorTag, ProcessorTag, ProcessorTag],
    ) -> None:
        entries = await l_make.n_entries_list(loaded_feed_id, 3)
        another_entries = await l_make.n_entries_list(another_loaded_feed_id, 3)

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
    @pytest.mark.asyncio
    async def test_no_feed(self) -> None:
        await limit_entries_for_feed(uuid.uuid4(), limit=10)

    @pytest.mark.asyncio
    async def test_no_entries(self, loaded_feed_id: uuid.UUID) -> None:
        await limit_entries_for_feed(loaded_feed_id, limit=10)

    @pytest.mark.asyncio
    async def test_not_exceed_limit(self, loaded_feed_id: uuid.UUID) -> None:
        entries = await l_make.n_entries_list(loaded_feed_id, 3)

        await limit_entries_for_feed(loaded_feed_id, limit=10)

        loaded_entries = await l_domain.get_entries_by_filter(feeds_ids=[loaded_feed_id], limit=100)

        assert loaded_entries == entries

    @pytest.mark.asyncio
    async def test_exceed_limit(self, loaded_feed_id: uuid.UUID) -> None:
        entries = await l_make.n_entries_list(loaded_feed_id, 10)

        await limit_entries_for_feed(loaded_feed_id, limit=5)

        loaded_entries = await l_domain.get_entries_by_filter(feeds_ids=[loaded_feed_id], limit=100)

        assert loaded_entries == entries[:5]
