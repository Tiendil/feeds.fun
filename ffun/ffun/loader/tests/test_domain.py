import uuid
from collections.abc import Iterable

import pytest
from pytest_mock import MockerFixture
from structlog.testing import capture_logs

from ffun.core.tests.helpers import (
    assert_logs,
    assert_logs_has_business_event,
    assert_logs_has_no_business_event,
    assert_logs_has_record,
)
from ffun.domain.entities import EntryId, UserId
from ffun.domain.urls import str_to_feed_url, url_to_uid
from ffun.feeds import domain as f_domain
from ffun.feeds import entities as f_entities
from ffun.feeds_collections.collections import collections
from ffun.feeds_collections.entities import CollectionId
from ffun.feeds_links import domain as fl_domain
from ffun.library import domain as l_domain
from ffun.library import entities as l_entities
from ffun.loader import errors as lo_errors
from ffun.loader.domain import (
    check_proxies_availability,
    detect_orphaned,
    load_decoded_content,
    process_feed,
    store_entries,
    sync_feed_info,
)
from ffun.loader.settings import Proxy, settings
from ffun.parsers import entities as p_entities
from ffun.parsers.tests import make as p_make


def assert_entry_fields_equal_to_info(entry_info: p_entities.EntryInfo, entry: l_entities.Entry) -> None:
    assert entry.title == entry_info.title
    assert entry.body == entry_info.body
    assert entry.external_id == entry_info.external_id
    assert entry.external_url == entry_info.external_url
    assert entry.external_tags == entry_info.external_tags


def assert_entriy_equal_to_info(entry_info: p_entities.EntryInfo, entry: l_entities.Entry) -> None:
    assert_entry_fields_equal_to_info(entry_info, entry)
    assert entry.published_at == entry_info.published_at


@pytest.fixture  # type: ignore
def pushed_entries_to_process(mocker: MockerFixture) -> set[EntryId]:
    pushed_entries: set[EntryId] = set()

    async def fake_push_entries_to_process(entry_ids: Iterable[EntryId]) -> None:
        pushed_entries.update(entry_ids)

    mocker.patch("ffun.loader.domain.d_domain.push_entries_to_process", side_effect=fake_push_entries_to_process)

    return pushed_entries


class TestLoadDecodedContent:
    @pytest.mark.asyncio
    async def test_returns_decoded_content(self, mocker: MockerFixture) -> None:
        headers = {"User-Agent": "test-agent"}

        async def fake_load_content_with_proxies(url: object, headers: object = None) -> object:
            assert url == "https://example.com/feed"
            assert headers == {"User-Agent": "test-agent"}
            return object()

        async def fake_decode_content(response: object) -> str:
            assert response is not None
            return "<feed>content</feed>"

        mocker.patch("ffun.loader.domain.load_content_with_proxies", side_effect=fake_load_content_with_proxies)
        mocker.patch("ffun.loader.domain.decode_content", side_effect=fake_decode_content)

        assert await load_decoded_content(str_to_feed_url("https://example.com/feed"), headers=headers) == (
            "<feed>content</feed>"
        )

    @pytest.mark.asyncio
    async def test_returns_none_on_load_error(self, mocker: MockerFixture) -> None:
        async def fake_load_content_with_proxies(url: object, headers: object = None) -> object:
            assert url == "https://example.com/feed"
            assert headers is None
            raise lo_errors.LoadError(feed_error_code=f_entities.FeedError.network_connection_timeout)

        mocker.patch("ffun.loader.domain.load_content_with_proxies", side_effect=fake_load_content_with_proxies)

        with capture_logs() as logs:  # type: ignore
            assert await load_decoded_content(str_to_feed_url("https://example.com/feed")) is None

        assert_logs_has_record(
            logs,  # type: ignore
            "load_decoded_content_error",
            url="https://example.com/feed",
            error_code=f_entities.FeedError.network_connection_timeout,
        )

    @pytest.mark.asyncio
    async def test_raises_load_error_when_none_on_error_disabled(self, mocker: MockerFixture) -> None:
        async def fake_load_content_with_proxies(url: object, headers: object = None) -> object:
            assert url == "https://example.com/feed"
            assert headers is None
            raise lo_errors.LoadError(feed_error_code=f_entities.FeedError.network_connection_timeout)

        mocker.patch("ffun.loader.domain.load_content_with_proxies", side_effect=fake_load_content_with_proxies)

        with capture_logs() as logs:  # type: ignore
            with pytest.raises(lo_errors.LoadError):
                await load_decoded_content(str_to_feed_url("https://example.com/feed"), none_on_error=False)

        assert_logs_has_record(
            logs,  # type: ignore
            "load_decoded_content_error",
            url="https://example.com/feed",
            error_code=f_entities.FeedError.network_connection_timeout,
        )

    @pytest.mark.asyncio
    async def test_logs_and_returns_none_on_unexpected_error(self, mocker: MockerFixture) -> None:
        async def fake_load_content_with_proxies(url: object, headers: object = None) -> object:
            assert url == "https://example.com/feed"
            assert headers is None
            raise RuntimeError("boom")

        mocker.patch("ffun.loader.domain.load_content_with_proxies", side_effect=fake_load_content_with_proxies)

        with capture_logs() as logs:  # type: ignore
            assert await load_decoded_content(str_to_feed_url("https://example.com/feed")) is None

        assert_logs_has_record(
            logs,  # type: ignore
            "unexpected_error_while_loading_decoded_content",
            url="https://example.com/feed",
        )

    @pytest.mark.asyncio
    async def test_logs_and_raises_unexpected_error_when_none_on_error_disabled(self, mocker: MockerFixture) -> None:
        async def fake_load_content_with_proxies(url: object, headers: object = None) -> object:
            assert url == "https://example.com/feed"
            assert headers is None
            raise RuntimeError("boom")

        mocker.patch("ffun.loader.domain.load_content_with_proxies", side_effect=fake_load_content_with_proxies)

        with capture_logs() as logs:  # type: ignore
            with pytest.raises(RuntimeError):
                await load_decoded_content(str_to_feed_url("https://example.com/feed"), none_on_error=False)

        assert_logs_has_record(
            logs,  # type: ignore
            "unexpected_error_while_loading_decoded_content",
            url="https://example.com/feed",
        )


async def assert_filtered_entry_equal_to_info(entry_info: p_entities.EntryInfo, entry: l_entities.Entry) -> None:
    assert_entry_fields_equal_to_info(entry_info, entry)
    assert entry.published_at is not None

    loaded_entry = await l_domain.get_entry(entry.id)

    assert_entriy_equal_to_info(entry_info, loaded_entry)
    assert entry.published_at == loaded_entry.published_at


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
    async def test_no_entries(self, saved_feed: f_entities.Feed, pushed_entries_to_process: set[EntryId]) -> None:
        with capture_logs() as logs:  # type: ignore
            await store_entries(saved_feed, [])

        assert_logs(logs, news_entries_stored=0)  # type: ignore
        assert_logs_has_record(logs, "entries_stored", entries_cataloged=0, entries_skipped=0)  # type: ignore
        assert_logs_has_no_business_event(logs, "news_entries_stored")  # type: ignore

        entries = await l_domain.get_entries_by_filter([saved_feed.id], limit=1)

        assert not entries
        assert pushed_entries_to_process == set()

    @pytest.mark.asyncio
    async def test_save_new_entries(
        self, saved_feed: f_entities.Feed, pushed_entries_to_process: set[EntryId]
    ) -> None:
        n = 3

        entry_infos = [p_make.fake_entry_info() for _ in range(n)]

        with capture_logs() as logs:  # type: ignore
            await store_entries(saved_feed, entry_infos)

        assert_logs_has_record(logs, "entries_stored", entries_cataloged=n, entries_skipped=0)  # type: ignore
        assert_logs_has_business_event(
            logs, "news_entries_stored", user_id=None, feed_id=str(saved_feed.id), entries_number=n  # type: ignore
        )

        loaded_entries = await l_domain.get_entries_by_filter([saved_feed.id], limit=n + 1)

        assert len(loaded_entries) == 3

        assert pushed_entries_to_process == {entry.id for entry in loaded_entries}

        entry_infos.sort(key=lambda e: e.title)
        loaded_entries.sort(key=lambda e: e.title)

        for entry_info, entry in zip(entry_infos, loaded_entries):
            assert entry.source_id == saved_feed.source_id
            await assert_filtered_entry_equal_to_info(entry_info, entry)

    @pytest.mark.asyncio
    async def test_save_in_parts(self, saved_feed: f_entities.Feed, pushed_entries_to_process: set[EntryId]) -> None:
        n = 5
        m = 3

        assert m < n

        entry_infos = [p_make.fake_entry_info() for _ in range(n)]
        entry_infos.sort(key=lambda e: e.title)

        with capture_logs() as logs:  # type: ignore
            await store_entries(saved_feed, entry_infos[:m])

        assert_logs_has_record(logs, "entries_stored", entries_cataloged=m, entries_skipped=0)  # type: ignore
        assert_logs_has_business_event(
            logs, "news_entries_stored", user_id=None, feed_id=str(saved_feed.id), entries_number=m  # type: ignore
        )

        loaded_entries = await l_domain.get_entries_by_filter([saved_feed.id], limit=n + 1)

        assert len(loaded_entries) == m
        first_entries_ids = {entry.id for entry in loaded_entries}

        assert pushed_entries_to_process == first_entries_ids
        pushed_entries_to_process.clear()

        loaded_entries.sort(key=lambda e: e.title)

        for entry_info, entry in zip(entry_infos, loaded_entries):
            assert entry.source_id == saved_feed.source_id
            await assert_filtered_entry_equal_to_info(entry_info, entry)

        with capture_logs() as logs:  # type: ignore
            await store_entries(saved_feed, entry_infos)

        assert_logs_has_record(logs, "entries_stored", entries_cataloged=n - m, entries_skipped=m)  # type: ignore
        assert_logs_has_business_event(
            logs, "news_entries_stored", user_id=None, feed_id=str(saved_feed.id), entries_number=n - m  # type: ignore
        )

        loaded_entries = await l_domain.get_entries_by_filter([saved_feed.id], limit=n + 1)

        assert len(loaded_entries) == n
        second_entries_ids = {entry.id for entry in loaded_entries} - first_entries_ids

        assert pushed_entries_to_process == second_entries_ids

        loaded_entries.sort(key=lambda e: e.title)

        for entry_info, entry in zip(entry_infos, loaded_entries):
            assert entry.source_id == saved_feed.source_id
            await assert_filtered_entry_equal_to_info(entry_info, entry)

    @pytest.mark.asyncio
    async def test_skip_all_entries(
        self, saved_feed: f_entities.Feed, pushed_entries_to_process: set[EntryId]
    ) -> None:
        entry_infos = [p_make.fake_entry_info() for _ in range(3)]

        await store_entries(saved_feed, entry_infos)
        pushed_entries_to_process.clear()

        with capture_logs() as logs:  # type: ignore
            await store_entries(saved_feed, entry_infos)

        assert_logs_has_record(logs, "entries_stored", entries_cataloged=0, entries_skipped=3)  # type: ignore
        assert_logs_has_no_business_event(logs, "news_entries_stored")  # type: ignore
        assert pushed_entries_to_process == set()


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

        with capture_logs() as logs:  # type: ignore
            await process_feed(feed=saved_feed)

        assert_logs(logs, feed_has_no_entries_tail=1, feed_entries_tail_removed=0)  # type: ignore

        extract_feed_info.assert_called_once_with(feed_id=saved_feed.id, feed_url=saved_feed.url)

        loaded_entries = await l_domain.get_entries_by_filter([saved_feed.id], limit=n + 1)

        assert len(loaded_entries) == n

        entry_infos.sort(key=lambda e: e.title)
        loaded_entries.sort(key=lambda e: e.title)

        for entry_info, entry in zip(entry_infos, loaded_entries):
            assert entry.source_id == saved_feed.source_id
            await assert_filtered_entry_equal_to_info(entry_info, entry)

    @pytest.mark.asyncio
    async def test_cleanup_logic_called__when_feed_is_updated(
        self, internal_user_id: UserId, saved_feed: f_entities.Feed, mocker: MockerFixture
    ) -> None:
        entry_infos = [p_make.fake_entry_info() for _ in range(5)]

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
        shrink_feed = mocker.patch("ffun.loader.domain.l_domain.shrink_feed")

        await fl_domain.add_link(internal_user_id, saved_feed.id)

        await process_feed(feed=saved_feed)

        extract_feed_info.assert_called_once_with(feed_id=saved_feed.id, feed_url=saved_feed.url)
        assert shrink_feed.call_args_list == [mocker.call(saved_feed.id)]  # type: ignore

    @pytest.mark.asyncio
    async def test_cleanup_logic_called__when_feed_is_not_updated(
        self, internal_user_id: UserId, saved_feed: f_entities.Feed, mocker: MockerFixture
    ) -> None:
        entry_infos = [p_make.fake_entry_info() for _ in range(5)]
        entry_infos.sort(key=lambda e: e.title)

        await store_entries(saved_feed, entry_infos)

        extract_feed_info = mocker.patch("ffun.loader.domain.extract_feed_info", return_value=None)
        shrink_feed = mocker.patch("ffun.loader.domain.l_domain.shrink_feed")

        await fl_domain.add_link(internal_user_id, saved_feed.id)

        await process_feed(feed=saved_feed)

        extract_feed_info.assert_called_once_with(feed_id=saved_feed.id, feed_url=saved_feed.url)
        assert shrink_feed.call_args_list == [mocker.call(saved_feed.id)]  # type: ignore


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
            is_proxy_available.assert_any_call(proxy=proxy, anchors=settings.proxy_anchors)
