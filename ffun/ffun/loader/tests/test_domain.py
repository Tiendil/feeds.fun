import uuid

import pytest
from pytest_mock import MockerFixture
from structlog.testing import capture_logs

from ffun.core.tests.helpers import assert_logs
from ffun.domain.entities import UserId
from ffun.domain.urls import url_to_uid
from ffun.feeds import domain as f_domain
from ffun.feeds import entities as f_entities
from ffun.feeds_collections.collections import collections
from ffun.feeds_collections.entities import CollectionId
from ffun.feeds_links import domain as fl_domain
from ffun.library import domain as l_domain
from ffun.library import entities as l_entities
from ffun.loader.domain import check_proxies_availability, detect_orphaned, process_feed, store_entries, sync_feed_info
from ffun.loader.settings import Proxy, settings
from ffun.parsers import entities as p_entities
from ffun.parsers.tests import make as p_make


def assert_entriy_equal_to_info(entry_info: p_entities.EntryInfo, entry: l_entities.Entry) -> None:
    assert entry.title == entry_info.title
    assert entry.body == entry_info.body
    assert entry.external_id == entry_info.external_id
    assert entry.external_url == entry_info.external_url
    assert entry.external_tags == entry_info.external_tags
    assert entry.published_at == entry_info.published_at


class TestDetectOrphaned:
    @pytest.mark.asyncio
    async def test_is_orphaned(self, saved_feed_id: f_entities.FeedId) -> None:
        assert await detect_orphaned(saved_feed_id)

        loaded_feed = await f_domain.get_feed(saved_feed_id)

        assert loaded_feed.state == f_entities.FeedState.orphaned

    @pytest.mark.asyncio
    async def test_is_orphaned_but_from_collection(
        self,
        saved_feed_id: f_entities.FeedId,
        collection_id_for_test_feeds: CollectionId,
    ) -> None:
        await collections.add_test_feed_to_collections(collection_id_for_test_feeds, saved_feed_id)

        assert not await detect_orphaned(saved_feed_id)

        loaded_feed = await f_domain.get_feed(saved_feed_id)

        assert loaded_feed.state != f_entities.FeedState.orphaned

    @pytest.mark.asyncio
    async def test_not_orphaned(self, internal_user_id: UserId, saved_feed_id: f_entities.FeedId) -> None:
        await fl_domain.add_link(internal_user_id, saved_feed_id)

        assert not await detect_orphaned(saved_feed_id)

        loaded_feed = await f_domain.get_feed(saved_feed_id)

        assert loaded_feed.state != f_entities.FeedState.orphaned


class TestSyncFeedInfo:
    @pytest.mark.asyncio
    async def test_no_sync_required(self, saved_feed: f_entities.Feed, mocker: MockerFixture) -> None:
        update_feed_info = mocker.patch("ffun.feeds.domain.update_feed_info")

        assert saved_feed.title
        assert saved_feed.description

        feed_info = p_entities.FeedInfo(
            url=saved_feed.url,
            title=saved_feed.title,
            description=saved_feed.description,
            entries=[],
            uid=url_to_uid(saved_feed.url),
        )

        await sync_feed_info(saved_feed, feed_info)

        update_feed_info.assert_not_called()

    @pytest.mark.asyncio
    async def test_sync_required(self, saved_feed: f_entities.Feed) -> None:
        feed_info = p_entities.FeedInfo(
            url=saved_feed.url,
            title=uuid.uuid4().hex,
            description=uuid.uuid4().hex,
            entries=[],
            uid=url_to_uid(saved_feed.url),
        )

        await sync_feed_info(saved_feed, feed_info)

        loaded_feed = await f_domain.get_feed(saved_feed.id)

        assert loaded_feed.title == feed_info.title
        assert loaded_feed.description == feed_info.description

    @pytest.mark.asyncio
    async def test_sync_required__collections(
        self, collection_id_for_test_feeds: CollectionId, saved_feed: f_entities.Feed
    ) -> None:
        await collections.add_test_feed_to_collections(collection_id_for_test_feeds, saved_feed.id)

        feed_info = p_entities.FeedInfo(
            url=saved_feed.url,
            title=uuid.uuid4().hex,
            description=uuid.uuid4().hex,
            entries=[],
            uid=url_to_uid(saved_feed.url),
        )

        await sync_feed_info(saved_feed, feed_info)

        loaded_feed = await f_domain.get_feed(saved_feed.id)

        assert loaded_feed.title != feed_info.title
        assert loaded_feed.description != feed_info.description

        collection_feed_info = collections.get_feed_info(saved_feed.id)

        assert loaded_feed.title == collection_feed_info.title
        assert loaded_feed.description == collection_feed_info.description


class TestStoreEntries:
    @pytest.mark.asyncio
    async def test_no_entries(self, saved_feed: f_entities.Feed) -> None:
        await store_entries(saved_feed, [])

        entries = await l_domain.get_entries_by_filter([saved_feed.id], limit=1)

        assert not entries

    @pytest.mark.asyncio
    async def test_save_new_entries(self, saved_feed: f_entities.Feed) -> None:
        n = 3

        entry_infos = [p_make.fake_entry_info() for _ in range(n)]

        await store_entries(saved_feed, entry_infos)

        loaded_entries = await l_domain.get_entries_by_filter([saved_feed.id], limit=n + 1)

        assert len(loaded_entries) == 3

        entry_infos.sort(key=lambda e: e.title)
        loaded_entries.sort(key=lambda e: e.title)

        for entry_info, entry in zip(entry_infos, loaded_entries):
            assert entry.source_id == saved_feed.source_id
            assert_entriy_equal_to_info(entry_info, entry)

    @pytest.mark.asyncio
    async def test_save_in_parts(self, saved_feed: f_entities.Feed) -> None:
        n = 5
        m = 3

        assert m < n

        entry_infos = [p_make.fake_entry_info() for _ in range(n)]
        entry_infos.sort(key=lambda e: e.title)

        await store_entries(saved_feed, entry_infos[:m])

        loaded_entries = await l_domain.get_entries_by_filter([saved_feed.id], limit=n + 1)

        assert len(loaded_entries) == m

        loaded_entries.sort(key=lambda e: e.title)

        for entry_info, entry in zip(entry_infos, loaded_entries):
            assert entry.source_id == saved_feed.source_id
            assert_entriy_equal_to_info(entry_info, entry)

        await store_entries(saved_feed, entry_infos)

        loaded_entries = await l_domain.get_entries_by_filter([saved_feed.id], limit=n + 1)

        assert len(loaded_entries) == n

        loaded_entries.sort(key=lambda e: e.title)

        for entry_info, entry in zip(entry_infos, loaded_entries):
            assert entry.source_id == saved_feed.source_id
            assert_entriy_equal_to_info(entry_info, entry)


class TestProcessFeed:
    @pytest.mark.asyncio
    async def test_orphaned_feed(self, saved_feed: f_entities.Feed) -> None:
        assert await detect_orphaned(saved_feed.id)

        await process_feed(feed=saved_feed)

        loaded_feed = await f_domain.get_feed(saved_feed.id)

        assert loaded_feed.state == f_entities.FeedState.orphaned

        loaded_entries = await l_domain.get_entries_by_filter([saved_feed.id], limit=1)

        assert not loaded_entries

    @pytest.mark.asyncio
    async def test_can_not_extract_feed(
        self, internal_user_id: UserId, saved_feed: f_entities.Feed, mocker: MockerFixture
    ) -> None:
        extract_feed_info = mocker.patch("ffun.loader.domain.extract_feed_info", return_value=None)

        await fl_domain.add_link(internal_user_id, saved_feed.id)

        await process_feed(feed=saved_feed)

        extract_feed_info.assert_called_once_with(feed_id=saved_feed.id, feed_url=saved_feed.url)

        loaded_entries = await l_domain.get_entries_by_filter([saved_feed.id], limit=1)

        assert not loaded_entries

    @pytest.mark.asyncio
    async def test_success(self, internal_user_id: UserId, saved_feed: f_entities.Feed, mocker: MockerFixture) -> None:
        n = 3

        entry_infos = [p_make.fake_entry_info() for _ in range(n)]
        entry_infos.sort(key=lambda e: e.title)

        assert saved_feed.title
        assert saved_feed.description

        feed_info = p_entities.FeedInfo(
            url=saved_feed.url,
            title=saved_feed.title,
            description=saved_feed.description,
            entries=entry_infos,
            uid=url_to_uid(saved_feed.url),
        )

        extract_feed_info = mocker.patch("ffun.loader.domain.extract_feed_info", return_value=feed_info)

        await fl_domain.add_link(internal_user_id, saved_feed.id)

        with capture_logs() as logs:
            await process_feed(feed=saved_feed)

        assert_logs(logs, feed_has_no_entries_tail=1, feed_entries_tail_removed=0)

        extract_feed_info.assert_called_once_with(feed_id=saved_feed.id, feed_url=saved_feed.url)

        loaded_entries = await l_domain.get_entries_by_filter([saved_feed.id], limit=n + 1)

        assert len(loaded_entries) == n

        entry_infos.sort(key=lambda e: e.title)
        loaded_entries.sort(key=lambda e: e.title)

        for entry_info, entry in zip(entry_infos, loaded_entries):
            assert entry.source_id == saved_feed.source_id
            assert_entriy_equal_to_info(entry_info, entry)

    @pytest.mark.asyncio
    async def test_remove_too_long_entries_tail(
        self, internal_user_id: UserId, saved_feed: f_entities.Feed, mocker: MockerFixture
    ) -> None:
        n = 5
        m = 3

        entry_infos = [p_make.fake_entry_info() for _ in range(n)]
        entry_infos.sort(key=lambda e: e.title)

        assert saved_feed.title
        assert saved_feed.description

        feed_info = p_entities.FeedInfo(
            url=saved_feed.url,
            title=saved_feed.title,
            description=saved_feed.description,
            entries=entry_infos,
            uid=url_to_uid(saved_feed.url),
        )

        mocker.patch("ffun.loader.domain.extract_feed_info", return_value=feed_info)
        mocker.patch("ffun.library.settings.settings.max_entries_per_feed", m)

        await fl_domain.add_link(internal_user_id, saved_feed.id)

        with capture_logs() as logs:
            await process_feed(feed=saved_feed)

        assert_logs(logs, feed_has_no_entries_tail=0, feed_entries_tail_removed=1)

        loaded_entries = await l_domain.get_entries_by_filter([saved_feed.id], limit=n + 1)

        assert len(loaded_entries) == m


class TestCheckProxiesAvailability:
    @pytest.mark.asyncio
    async def test_no_proxies(self, mocker: MockerFixture) -> None:
        mocker.patch("ffun.loader.settings.settings.proxies", [])

        is_proxy_available = mocker.patch("ffun.loader.operations.is_proxy_available")

        await check_proxies_availability()

        is_proxy_available.assert_not_called()

    @pytest.mark.asyncio
    async def test_proxies(self, mocker: MockerFixture) -> None:
        n = 3

        proxies = [Proxy(name=uuid.uuid4().hex, url=None) for _ in range(n)]

        mocker.patch("ffun.loader.settings.settings.proxies", proxies)

        is_proxy_available = mocker.patch("ffun.loader.operations.is_proxy_available")

        await check_proxies_availability()

        for proxy in proxies:
            is_proxy_available.assert_any_call(proxy=proxy, anchors=settings.proxy_anchors, user_agent="unknown")
