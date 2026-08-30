import datetime
import uuid

import pytest
from pytest_mock import MockerFixture

from ffun.dispatcher import entries_cache
from ffun.dispatcher.entities import EntryProcessingStatus, EntryToProcess
from ffun.dispatcher.tests import make
from ffun.domain.domain import new_entry_id, new_feed_id, new_user_id
from ffun.domain.entities import EntryId, FeedId, ProcessorId, UserId
from ffun.entitlements.entities import EntitlementKindId
from ffun.entitlements.tests import make as e_make
from ffun.feeds.entities import Feed
from ffun.feeds_collections.entities import CollectionId
from ffun.feeds_collections.tests import helpers as fc_helpers
from ffun.library import domain as l_domain
from ffun.library.tests import make as l_make
from ffun.llms_framework.entities import KeyStatus, LLMProvider
from ffun.llms_framework.providers import llm_providers
from ffun.product.entities import UserSetting
from ffun.user_settings import domain as us_domain
from ffun.user_settings.entities import SettingKind


class TestEntryFeedIds:
    @pytest.mark.asyncio
    async def test_duplicate_entries(self, loaded_feed: Feed) -> None:
        entry = (await l_make.n_entries_list(loaded_feed, 1))[0]

        assert await entries_cache._entry_feed_ids([entry.id, entry.id]) == {  # noqa: SLF001
            entry.id: {loaded_feed.id}
        }

    @pytest.mark.asyncio
    async def test_returns_all_feed_links_and_skips_unlinked_entries(
        self,
        loaded_feed: Feed,
        another_loaded_feed: Feed,
    ) -> None:
        entries = await l_make.n_entries_list(loaded_feed, 2)
        unlinked_entry_id = new_entry_id()

        await l_domain.catalog_entries(
            another_loaded_feed.id,
            [entries[0].collected_entry()],
        )

        assert await entries_cache._entry_feed_ids(  # noqa: SLF001
            [entries[0].id, entries[1].id, unlinked_entry_id]
        ) == {
            entries[0].id: {loaded_feed.id, another_loaded_feed.id},
            entries[1].id: {loaded_feed.id},
        }


class TestEntryIdsInCollections:
    @pytest.mark.asyncio
    async def test_maps_collection_membership(
        self,
        loaded_feed: Feed,
        another_loaded_feed: Feed,
        collection_id_for_test_feeds: CollectionId,
    ) -> None:
        collection_entry_id = new_entry_id()
        user_entry_id = new_entry_id()
        entry_without_feeds_id = new_entry_id()

        await fc_helpers.add_feed_to_collection(collection_id_for_test_feeds, another_loaded_feed.id)

        assert entries_cache._entry_ids_in_collections(  # noqa: SLF001
            {
                collection_entry_id: {another_loaded_feed.id},
                user_entry_id: {loaded_feed.id},
                entry_without_feeds_id: set(),
            }
        ) == {collection_entry_id}


class TestEntriesInCollections:
    @pytest.mark.asyncio
    async def test_no_entries(self) -> None:
        assert await entries_cache.entries_in_collections([]) == set()

    @pytest.mark.asyncio
    async def test_returns_collection_membership(
        self,
        loaded_feed: Feed,
        another_loaded_feed: Feed,
        collection_id_for_test_feeds: CollectionId,
    ) -> None:
        user_entries = await l_make.n_entries(loaded_feed, 2)
        collection_entries = await l_make.n_entries(another_loaded_feed, 3)

        await fc_helpers.add_feed_to_collection(collection_id_for_test_feeds, another_loaded_feed.id)

        entries_in_collections = await entries_cache.entries_in_collections(
            list(user_entries) + list(collection_entries)
        )

        assert entries_in_collections == set(collection_entries)

    @pytest.mark.asyncio
    async def test_returns_collection_membership_for_entries_linked_to_multiple_feeds(
        self,
        loaded_feed: Feed,
        another_loaded_feed: Feed,
        collection_id_for_test_feeds: CollectionId,
    ) -> None:
        entries = await l_make.n_entries_list(loaded_feed, 3)

        await l_domain.catalog_entries(
            another_loaded_feed.id,
            [entry.collected_entry() for entry in entries[:2]],
        )
        await fc_helpers.add_feed_to_collection(collection_id_for_test_feeds, another_loaded_feed.id)

        entries_in_collections = await entries_cache.entries_in_collections([entry.id for entry in entries])

        assert entries_in_collections == {entries[0].id, entries[1].id}

    @pytest.mark.asyncio
    async def test_skips_entries_without_feed_links(self) -> None:
        entry_id = new_entry_id()

        assert await entries_cache.entries_in_collections([entry_id]) == set()


class TestUsersWithApiKeys:
    @pytest.mark.asyncio
    async def test_no_users(self) -> None:
        assert await entries_cache._users_with_api_keys([]) == set()  # noqa: SLF001

    @pytest.mark.asyncio
    async def test_duplicate_users(self) -> None:
        user_id = new_user_id()
        await us_domain.save_setting(
            user_id=user_id,
            kind=SettingKind(int(UserSetting.test_api_key)),
            value=uuid.uuid4().hex,
        )

        assert await entries_cache._users_with_api_keys([user_id, user_id]) == {user_id}  # noqa: SLF001

    @pytest.mark.asyncio
    async def test_detects_all_supported_api_key_settings(self) -> None:
        user_ids = [new_user_id() for _ in range(4)]
        api_key_settings = (
            UserSetting.openai_api_key,
            UserSetting.gemini_api_key,
            UserSetting.test_api_key,
        )

        for user_id, setting in zip(user_ids, api_key_settings, strict=False):
            await us_domain.save_setting(
                user_id=user_id,
                kind=SettingKind(int(setting)),
                value=uuid.uuid4().hex,
            )

        await us_domain.save_setting(
            user_id=user_ids[3],
            kind=SettingKind(int(UserSetting.test_api_key)),
            value="",
        )

        assert await entries_cache._users_with_api_keys(user_ids) == set(user_ids[:3])  # noqa: SLF001

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("status", "expected"),
        (
            (KeyStatus.unknown, True),
            (KeyStatus.works, True),
            (KeyStatus.broken, False),
            (KeyStatus.quota, False),
        ),
    )
    async def test_filters_by_api_key_status(self, status: KeyStatus, expected: bool) -> None:
        user_id = new_user_id()
        api_key = uuid.uuid4().hex
        await us_domain.save_setting(
            user_id=user_id,
            kind=SettingKind(int(UserSetting.test_api_key)),
            value=api_key,
        )
        llm_providers.get(LLMProvider.test).provider.api_keys_statuses.set(api_key, status)

        users_with_api_keys = await entries_cache._users_with_api_keys([user_id])  # noqa: SLF001

        assert (user_id in users_with_api_keys) is expected

    @pytest.mark.asyncio
    async def test_uses_status_of_matching_provider(self) -> None:
        openai_user_id = new_user_id()
        gemini_user_id = new_user_id()
        api_key = uuid.uuid4().hex
        await us_domain.save_setting(
            user_id=openai_user_id,
            kind=SettingKind(int(UserSetting.openai_api_key)),
            value=api_key,
        )
        await us_domain.save_setting(
            user_id=gemini_user_id,
            kind=SettingKind(int(UserSetting.gemini_api_key)),
            value=api_key,
        )
        llm_providers.get(LLMProvider.openai).provider.api_keys_statuses.set(api_key, KeyStatus.broken)
        llm_providers.get(LLMProvider.google).provider.api_keys_statuses.set(api_key, KeyStatus.works)

        assert await entries_cache._users_with_api_keys([openai_user_id, gemini_user_id]) == {  # noqa: SLF001
            gemini_user_id
        }


class TestEntriesCache:
    def test_entry_in_collection__membership_and_defaults(self) -> None:
        collection_entry_id = new_entry_id()
        user_entry_id = new_entry_id()
        missing_entry_id = new_entry_id()
        cache = entries_cache.EntriesCache(
            entry_ages={},
            entry_age_limits={},
            entries_in_collections={collection_entry_id},
            feed_ids_by_entry={},
            user_ids_by_feed={},
            users_with_api_keys=set(),
            processing_statuses={},
            entitlements={},
        )

        assert cache.entry_in_collection(collection_entry_id)
        assert not cache.entry_in_collection(user_entry_id)
        assert not cache.entry_in_collection(missing_entry_id)

    def test_entry_user_ids__merges_and_deduplicates_across_feeds(self) -> None:
        entry_id = new_entry_id()
        missing_entry_id = new_entry_id()
        first_feed_id = new_feed_id()
        second_feed_id = new_feed_id()
        first_user_id = new_user_id()
        shared_user_id = new_user_id()
        second_user_id = new_user_id()
        cache = entries_cache.EntriesCache(
            entry_ages={},
            entry_age_limits={},
            entries_in_collections=set(),
            feed_ids_by_entry={entry_id: {first_feed_id, second_feed_id}},
            user_ids_by_feed={
                first_feed_id: {first_user_id, shared_user_id},
                second_feed_id: {shared_user_id, second_user_id},
            },
            users_with_api_keys=set(),
            processing_statuses={},
            entitlements={},
        )

        assert cache.entry_user_ids(entry_id) == {
            first_user_id,
            shared_user_id,
            second_user_id,
        }
        assert cache.entry_user_ids(missing_entry_id) == set()

    def test_users_have_api_keys__only_for_selected_users(self) -> None:
        api_key_user_id = new_user_id()
        another_user_id = new_user_id()
        cache = entries_cache.EntriesCache(
            entry_ages={},
            entry_age_limits={},
            entries_in_collections=set(),
            feed_ids_by_entry={},
            user_ids_by_feed={},
            users_with_api_keys={api_key_user_id},
            processing_statuses={},
            entitlements={},
        )

        assert cache.users_have_api_keys([another_user_id, api_key_user_id])
        assert not cache.users_have_api_keys([another_user_id])
        assert not cache.users_have_api_keys([])

    def test_user_can_process_entry__compares_cached_age_and_limit(self) -> None:
        user_id = new_user_id()
        another_user_id = new_user_id()
        entry_id = new_entry_id()
        older_entry_id = new_entry_id()
        missing_entry_id = new_entry_id()
        cache = entries_cache.EntriesCache(
            entry_ages={
                entry_id: datetime.timedelta(days=1),
                older_entry_id: datetime.timedelta(days=1, microseconds=1),
            },
            entry_age_limits={user_id: datetime.timedelta(days=1)},
            entries_in_collections=set(),
            feed_ids_by_entry={},
            user_ids_by_feed={},
            users_with_api_keys=set(),
            processing_statuses={},
            entitlements={},
        )

        assert cache.user_can_process_entry(user_id, entry_id)
        assert not cache.user_can_process_entry(user_id, older_entry_id)
        assert not cache.user_can_process_entry(user_id, missing_entry_id)
        assert not cache.user_can_process_entry(another_user_id, entry_id)

    def test_user_entitlements__returns_cached_entitlements(self) -> None:
        user_id = new_user_id()
        entitlement = e_make.make_effective_entitlement_interval(user_id=user_id)
        user_entitlements = {
            EntitlementKindId.day_tokens: entitlement,
            EntitlementKindId.month_tokens: None,
        }
        cache = entries_cache.EntriesCache(
            entry_ages={},
            entry_age_limits={},
            entries_in_collections=set(),
            feed_ids_by_entry={},
            user_ids_by_feed={},
            users_with_api_keys=set(),
            processing_statuses={},
            entitlements={user_id: user_entitlements},
        )

        assert cache.user_entitlements(user_id) == user_entitlements

    def test_entry_processing_status__returns_status_and_defaults(self) -> None:
        processor_id = ProcessorId(101)
        another_processor_id = ProcessorId(102)
        entry_id = new_entry_id()
        missing_entry_id = new_entry_id()
        cache = entries_cache.EntriesCache(
            entry_ages={},
            entry_age_limits={},
            entries_in_collections=set(),
            feed_ids_by_entry={},
            user_ids_by_feed={},
            users_with_api_keys=set(),
            processing_statuses={
                processor_id: {
                    entry_id: EntryProcessingStatus.processed,
                }
            },
            entitlements={},
        )

        assert cache.entry_processing_status(processor_id, entry_id) == EntryProcessingStatus.processed
        assert cache.entry_processing_status(processor_id, missing_entry_id) is None
        assert cache.entry_processing_status(another_processor_id, entry_id) is None


class TestCreateEntriesCache:
    @pytest.mark.asyncio
    async def test_no_items_and_processors(self) -> None:
        cache = await entries_cache.create_entries_cache(
            [],
            [],
            entitlement_kind_ids=list(EntitlementKindId),
        )
        entry_id = new_entry_id()
        processor_id = ProcessorId(101)

        assert not cache.entry_in_collection(entry_id)
        assert cache.entry_user_ids(entry_id) == set()
        assert not cache.users_have_api_keys([new_user_id()])
        assert cache.entry_processing_status(processor_id, entry_id) is None

    @pytest.mark.asyncio
    async def test_bulk_loads_and_connects_cached_values(  # noqa: CFQ001
        self,
        loaded_feed: Feed,
        fake_processor_id: ProcessorId,
        another_fake_processor_id: ProcessorId,
        mocker: MockerFixture,
    ) -> None:
        collection_entry_id = new_entry_id()
        user_entry_id = new_entry_id()
        collection_feed_id = new_feed_id()
        user_feed_id = new_feed_id()
        api_key_user_id = new_user_id()
        another_user_id = new_user_id()
        items = [
            EntryToProcess(entry_id=collection_entry_id),
            EntryToProcess(entry_id=user_entry_id),
            EntryToProcess(entry_id=collection_entry_id),
        ]
        processors = [
            make.processor_dispatch_info(fake_processor_id),
            make.processor_dispatch_info(another_fake_processor_id),
        ]
        statuses = {
            fake_processor_id: {
                user_entry_id: EntryProcessingStatus.failed,
            },
            another_fake_processor_id: {},
        }
        feed_ids_by_entry: dict[EntryId, set[FeedId]] = {
            collection_entry_id: {collection_feed_id},
            user_entry_id: {user_feed_id},
        }
        user_ids_by_feed: dict[FeedId, set[UserId]] = {
            collection_feed_id: {api_key_user_id},
            user_feed_id: {api_key_user_id, another_user_id},
        }
        users_with_api_keys: set[UserId] = {api_key_user_id}
        now = datetime.datetime.now(tz=datetime.UTC)
        entries_by_id = {
            collection_entry_id: l_make.fake_entry(
                loaded_feed.source_id,
                id=collection_entry_id,
                published_at=now - datetime.timedelta(hours=1),
            ).fake_entry(created_at=now),
            user_entry_id: l_make.fake_entry(
                loaded_feed.source_id,
                id=user_entry_id,
                published_at=now - datetime.timedelta(days=2),
            ).fake_entry(created_at=now),
        }
        entry_age_limit_kind = SettingKind(int(UserSetting.process_entries_not_older_than))
        users_settings = {
            api_key_user_id: {entry_age_limit_kind: 1},
            another_user_id: {entry_age_limit_kind: 3},
        }
        entitlement = e_make.make_effective_entitlement_interval(user_id=another_user_id)
        entitlements = {
            api_key_user_id: {
                EntitlementKindId.day_tokens: None,
                EntitlementKindId.month_tokens: None,
            },
            another_user_id: {
                EntitlementKindId.day_tokens: entitlement,
                EntitlementKindId.month_tokens: None,
            },
        }
        entitlement_kind_ids = [
            EntitlementKindId.day_tokens,
            EntitlementKindId.month_tokens,
        ]
        entries_in_collections = {collection_entry_id}
        feed_ids = {collection_feed_id, user_feed_id}
        user_ids: set[UserId] = {api_key_user_id, another_user_id}
        entries_mock = mocker.patch.object(
            entries_cache.l_domain,
            "get_entries_by_ids",
            return_value=entries_by_id,
        )
        entry_feed_ids_mock = mocker.patch.object(
            entries_cache,
            "_entry_feed_ids",
            return_value=feed_ids_by_entry,
        )
        statuses_mock = mocker.patch.object(
            entries_cache.operations,
            "get_entries_processing_statuses",
            return_value=statuses,
        )
        linked_users_mock = mocker.patch.object(
            entries_cache.fl_domain,
            "get_linked_users",
            return_value=user_ids_by_feed,
        )
        api_key_users_mock = mocker.patch.object(
            entries_cache,
            "_users_with_api_keys",
            return_value=users_with_api_keys,
        )
        entitlements_mock = mocker.patch.object(
            entries_cache.e_domain,
            "get_entitlements",
            return_value=entitlements,
        )
        users_settings_mock = mocker.patch.object(
            entries_cache.us_domain,
            "load_settings_for_users",
            return_value=users_settings,
        )
        entry_ids_in_collections_mock = mocker.patch.object(
            entries_cache,
            "_entry_ids_in_collections",
            return_value=entries_in_collections,
        )

        cache = await entries_cache.create_entries_cache(
            items,
            processors,
            entitlement_kind_ids=entitlement_kind_ids,
        )

        entry_ids: set[EntryId] = {collection_entry_id, user_entry_id}
        selected_entry_ids = list(entry_ids)
        processor_ids = [fake_processor_id, another_fake_processor_id]
        entries_mock.assert_awaited_once_with(selected_entry_ids)
        entry_feed_ids_mock.assert_awaited_once_with(entry_ids)
        statuses_mock.assert_awaited_once_with(processor_ids, entry_ids)
        entry_ids_in_collections_mock.assert_called_once_with(feed_ids_by_entry)
        linked_users_mock.assert_awaited_once_with(feed_ids)
        api_key_users_mock.assert_awaited_once_with(user_ids)
        entitlements_mock.assert_awaited_once()
        users_settings_mock.assert_awaited_once_with(
            user_ids,
            kinds=(entry_age_limit_kind,),
        )
        assert cache.entry_in_collection(collection_entry_id)
        assert not cache.entry_in_collection(user_entry_id)
        assert cache.entry_user_ids(user_entry_id) == {api_key_user_id, another_user_id}
        assert cache.users_have_api_keys(cache.entry_user_ids(user_entry_id))
        assert not cache.user_can_process_entry(api_key_user_id, user_entry_id)
        assert cache.user_can_process_entry(another_user_id, user_entry_id)
        assert cache.user_entitlements(another_user_id) == entitlements[another_user_id]
        assert cache.entry_processing_status(fake_processor_id, user_entry_id) == EntryProcessingStatus.failed
