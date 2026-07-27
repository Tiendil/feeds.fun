import asyncio
from collections.abc import Iterable, Mapping, Sequence

from ffun.dispatcher import operations
from ffun.dispatcher.entities import EntryProcessingStatus, EntryToProcess, ProcessorDispatchInfo
from ffun.domain.entities import EntryId, FeedId, ProcessorId, UserId
from ffun.feeds_collections import domain as fc_domain
from ffun.feeds_links import domain as fl_domain
from ffun.library import domain as l_domain
from ffun.product.entities import UserSetting
from ffun.user_settings import domain as us_domain
from ffun.user_settings.entities import SettingKind

_API_KEY_SETTING_KINDS = tuple(
    SettingKind(int(setting))
    for setting in (
        UserSetting.openai_api_key,
        UserSetting.gemini_api_key,
        UserSetting.test_api_key,
    )
)


async def _entry_feed_ids(entries_ids: Iterable[EntryId]) -> dict[EntryId, set[FeedId]]:
    feed_links = await l_domain.get_feed_links_for_entries(entries_ids)

    return {entry_id: {link.feed_id for link in links} for entry_id, links in feed_links.items()}


def _entry_ids_in_collections(feed_ids_by_entry: Mapping[EntryId, set[FeedId]]) -> set[EntryId]:
    return {
        entry_id
        for entry_id, feed_ids in feed_ids_by_entry.items()
        if any(fc_domain.collections_for_feed(feed_id) for feed_id in feed_ids)
    }


async def entries_in_collections(entries_ids: Iterable[EntryId]) -> set[EntryId]:
    feed_ids_by_entry = await _entry_feed_ids(entries_ids)

    return _entry_ids_in_collections(feed_ids_by_entry)


class EntriesCache:
    __slots__ = (
        "_entries_in_collections",
        "_feed_ids_by_entry",
        "_processing_statuses",
        "_user_ids_by_feed",
        "_users_with_api_keys",
    )

    def __init__(
        self,
        entries_in_collections: set[EntryId],
        feed_ids_by_entry: Mapping[EntryId, set[FeedId]],
        user_ids_by_feed: Mapping[FeedId, set[UserId]],
        users_with_api_keys: set[UserId],
        processing_statuses: Mapping[ProcessorId, Mapping[EntryId, EntryProcessingStatus]],
    ) -> None:
        self._entries_in_collections = entries_in_collections
        self._feed_ids_by_entry = feed_ids_by_entry
        self._user_ids_by_feed = user_ids_by_feed
        self._users_with_api_keys = users_with_api_keys
        self._processing_statuses = processing_statuses

    def entry_in_collection(self, entry_id: EntryId) -> bool:
        return entry_id in self._entries_in_collections

    def entry_user_ids(self, entry_id: EntryId) -> set[UserId]:
        user_ids: set[UserId] = set()

        for feed_id in self._feed_ids_by_entry.get(entry_id, set()):
            user_ids.update(self._user_ids_by_feed.get(feed_id, set()))

        return user_ids

    def users_have_api_keys(self, user_ids: Iterable[UserId]) -> bool:
        return any(user_id in self._users_with_api_keys for user_id in user_ids)

    def entry_processing_status(
        self,
        processor_id: ProcessorId,
        entry_id: EntryId,
    ) -> EntryProcessingStatus | None:
        return self._processing_statuses.get(processor_id, {}).get(entry_id)


async def _users_with_api_keys(user_ids: Iterable[UserId]) -> set[UserId]:
    selected_user_ids = sorted(set(user_ids), key=str)
    users_settings = await us_domain.load_settings_for_users(
        selected_user_ids,
        kinds=_API_KEY_SETTING_KINDS,
    )

    return {
        user_id
        for user_id, settings in users_settings.items()
        if any(settings.get(kind) for kind in _API_KEY_SETTING_KINDS)
    }


async def create_entries_cache(
    items: Sequence[EntryToProcess],
    processors: Sequence[ProcessorDispatchInfo],
) -> EntriesCache:
    entry_ids = {item.entry_id for item in items}
    processor_ids = [processor.processor_id for processor in processors]
    feed_ids_by_entry, processing_statuses = await asyncio.gather(
        _entry_feed_ids(entry_ids),
        operations.get_entries_processing_statuses(processor_ids, entry_ids),
    )
    entries_in_collections = _entry_ids_in_collections(feed_ids_by_entry)
    feed_ids = {feed_id for entry_feed_ids in feed_ids_by_entry.values() for feed_id in entry_feed_ids}
    user_ids_by_feed = await fl_domain.get_linked_users(feed_ids)
    user_ids = {user_id for feed_user_ids in user_ids_by_feed.values() for user_id in feed_user_ids}
    users_with_api_keys = await _users_with_api_keys(user_ids)

    return EntriesCache(
        entries_in_collections=entries_in_collections,
        feed_ids_by_entry=feed_ids_by_entry,
        user_ids_by_feed=user_ids_by_feed,
        users_with_api_keys=users_with_api_keys,
        processing_statuses=processing_statuses,
    )
