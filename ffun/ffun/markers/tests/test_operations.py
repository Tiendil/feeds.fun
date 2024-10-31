import pytest

from ffun.core.postgresql import transaction
from ffun.core.tests.helpers import (
    TableSizeDelta,
    TableSizeNotChanged,
    assert_logs_has_business_event,
    assert_logs_has_no_business_event,
    capture_logs,
)
from ffun.domain.entities import UserId
from ffun.feeds.entities import Feed
from ffun.library.entities import Entry
from ffun.library.tests import make as l_make
from ffun.markers.entities import Marker
from ffun.markers.operations import (
    get_markers,
    remove_marker,
    remove_markers_for_entries,
    set_marker,
    tech_merge_markers,
)
from ffun.users.tests import make as u_make


class TestSetMarker:

    @pytest.mark.asyncio
    async def test_set_marker(self, internal_user_id: UserId, new_entry: Entry) -> None:
        with capture_logs() as logs:
            async with TableSizeDelta("m_markers", delta=1):
                await set_marker(internal_user_id, Marker.read, new_entry.id)

        assert_logs_has_business_event(
            logs, "marker_set", user_id=internal_user_id, entry_id=str(new_entry.id), marker=Marker.read
        )

    @pytest.mark.asyncio
    async def test_set_marker_twice(self, internal_user_id: UserId, new_entry: Entry) -> None:
        await set_marker(internal_user_id, Marker.read, new_entry.id)

        with capture_logs() as logs:
            async with TableSizeNotChanged("m_markers"):
                await set_marker(internal_user_id, Marker.read, new_entry.id)

        assert_logs_has_no_business_event(logs, "marker_set")


class TestRemoveMarker:

    @pytest.mark.asyncio
    async def test_remove_marker(self, internal_user_id: UserId, new_entry: Entry) -> None:
        await set_marker(internal_user_id, Marker.read, new_entry.id)

        with capture_logs() as logs:
            async with TableSizeDelta("m_markers", delta=-1):
                await remove_marker(internal_user_id, Marker.read, new_entry.id)

        assert_logs_has_business_event(
            logs, "marker_removed", user_id=internal_user_id, entry_id=str(new_entry.id), marker=Marker.read
        )

    @pytest.mark.asyncio
    async def test_remove_marker_twice(self, internal_user_id: UserId, new_entry: Entry) -> None:
        await set_marker(internal_user_id, Marker.read, new_entry.id)
        await remove_marker(internal_user_id, Marker.read, new_entry.id)

        with capture_logs() as logs:
            async with TableSizeNotChanged("m_markers"):
                await remove_marker(internal_user_id, Marker.read, new_entry.id)

        assert_logs_has_no_business_event(logs, "marker_removed")


class TestMergeFeeds:
    @pytest.mark.asyncio
    async def test_nothing_to_merge(self, new_entry: Entry, another_new_entry: Entry) -> None:
        async with transaction() as trx:
            await tech_merge_markers(trx, new_entry.id, another_new_entry.id)

    @pytest.mark.asyncio
    async def test_move_markers(self, loaded_feed: Feed) -> None:
        entry_1, entry_2, entry_3 = await l_make.n_entries_list(loaded_feed, 3)

        user_a, user_b = await u_make.n_users(2)

        await set_marker(user_a, Marker.read, entry_1.id)
        await set_marker(user_b, Marker.read, entry_2.id)

        async with TableSizeNotChanged("m_markers"):
            async with transaction() as trx:
                await tech_merge_markers(trx, from_entry_id=entry_2.id, to_entry_id=entry_3.id)

        markers_a = await get_markers(user_a, [entry_1.id, entry_2.id, entry_3.id])
        markers_b = await get_markers(user_b, [entry_1.id, entry_2.id, entry_3.id])

        assert markers_a == {entry_1.id: {Marker.read}}
        assert markers_b == {entry_3.id: {Marker.read}}

    @pytest.mark.asyncio
    async def test_rewrite_links(self, loaded_feed: Feed) -> None:
        entry_1, entry_2, entry_3 = await l_make.n_entries_list(loaded_feed, 3)

        user_a, user_b = await u_make.n_users(2)

        await set_marker(user_a, Marker.read, entry_1.id)
        await set_marker(user_b, Marker.read, entry_2.id)
        await set_marker(user_b, Marker.read, entry_3.id)

        async with TableSizeDelta("m_markers", delta=-1):
            async with transaction() as trx:
                await tech_merge_markers(trx, from_entry_id=entry_2.id, to_entry_id=entry_3.id)

        markers_a = await get_markers(user_a, [entry_1.id, entry_2.id, entry_3.id])
        markers_b = await get_markers(user_b, [entry_1.id, entry_2.id, entry_3.id])

        assert markers_a == {entry_1.id: {Marker.read}}
        assert markers_b == {entry_3.id: {Marker.read}}

    @pytest.mark.asyncio
    async def test_complex_ops(self, loaded_feed: Feed) -> None:
        entry_1, entry_2, entry_3 = await l_make.n_entries_list(loaded_feed, 3)

        user_a, user_b, user_c = await u_make.n_users(3)

        await set_marker(user_a, Marker.read, entry_1.id)

        await set_marker(user_b, Marker.read, entry_2.id)
        await set_marker(user_b, Marker.read, entry_3.id)

        await set_marker(user_c, Marker.read, entry_2.id)

        async with TableSizeDelta("m_markers", delta=-1):
            async with transaction() as trx:
                await tech_merge_markers(trx, from_entry_id=entry_2.id, to_entry_id=entry_3.id)

        markers_a = await get_markers(user_a, [entry_1.id, entry_2.id, entry_3.id])
        markers_b = await get_markers(user_b, [entry_1.id, entry_2.id, entry_3.id])
        markers_c = await get_markers(user_c, [entry_1.id, entry_2.id, entry_3.id])

        assert markers_a == {entry_1.id: {Marker.read}}
        assert markers_b == {entry_3.id: {Marker.read}}
        assert markers_c == {entry_3.id: {Marker.read}}


class TestRemoveMarkersForEntries:
    @pytest.mark.asyncio
    async def test_nothing_to_remove(self, loaded_feed: Feed) -> None:
        entry_1, entry_2, entry_3 = await l_make.n_entries_list(loaded_feed, 3)

        async with TableSizeNotChanged("m_markers"):
            await remove_markers_for_entries([entry_1.id, entry_2.id, entry_3.id])

    @pytest.mark.asyncio
    async def test_remove(self, loaded_feed: Feed) -> None:
        entry_1, entry_2, entry_3 = await l_make.n_entries_list(loaded_feed, 3)

        user_a, user_b, user_c = await u_make.n_users(3)

        await set_marker(user_a, Marker.read, entry_1.id)

        await set_marker(user_b, Marker.read, entry_2.id)
        await set_marker(user_b, Marker.read, entry_3.id)

        await set_marker(user_c, Marker.read, entry_2.id)

        async with TableSizeDelta("m_markers", delta=-3):
            await remove_markers_for_entries([entry_1.id, entry_2.id])

        markers_a = await get_markers(user_a, [entry_1.id, entry_2.id, entry_3.id])
        markers_b = await get_markers(user_b, [entry_1.id, entry_2.id, entry_3.id])
        markers_c = await get_markers(user_c, [entry_1.id, entry_2.id, entry_3.id])

        assert markers_a == {}
        assert markers_b == {entry_3.id: {Marker.read}}
        assert markers_c == {}
