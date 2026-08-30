import asyncio
import datetime
from collections.abc import Iterable, Mapping, Sequence

from ffun.dispatcher import operations
from ffun.dispatcher.entities import EntryProcessingStatus, EntryToProcess, ProcessorDispatchInfo
from ffun.domain.entities import EntryId, FeedId, ProcessorId, UserId
from ffun.entitlements import domain as e_domain
from ffun.entitlements.entities import EffectiveEntitlementInterval, EntitlementKindId
from ffun.feeds_collections import domain as fc_domain
from ffun.feeds_links import domain as fl_domain
from ffun.library import domain as l_domain

# Temporary architecture exception: this direct llms_framework.keys_rotator import is intentional.
# Consistency checks should ignore only this dependency while the legacy personal API-key bypass is supported.
# Remove it together with that bypass.
from ffun.llms_framework.keys_rotator import user_api_key_is_available  # tach-ignore
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

_ENTRY_AGE_LIMIT_SETTING_KIND = SettingKind(int(UserSetting.process_entries_not_older_than))


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
        "_entry_age_limits",
        "_entry_ages",
        "_entries_in_collections",
        "_entitlements",
        "_feed_ids_by_entry",
        "_processing_statuses",
        "_user_ids_by_feed",
        "_users_with_api_keys",
    )

    def __init__(  # noqa: CFQ002
        self,
        entries_in_collections: set[EntryId],
        feed_ids_by_entry: Mapping[EntryId, set[FeedId]],
        user_ids_by_feed: Mapping[FeedId, set[UserId]],
        users_with_api_keys: set[UserId],
        processing_statuses: Mapping[ProcessorId, Mapping[EntryId, EntryProcessingStatus]],
        entitlements: Mapping[
            UserId,
            Mapping[EntitlementKindId, EffectiveEntitlementInterval | None],
        ],
        entry_ages: Mapping[EntryId, datetime.timedelta],
        entry_age_limits: Mapping[UserId, datetime.timedelta],
    ) -> None:
        self._entry_ages = entry_ages
        self._entry_age_limits = entry_age_limits
        self._entries_in_collections = entries_in_collections
        self._feed_ids_by_entry = feed_ids_by_entry
        self._user_ids_by_feed = user_ids_by_feed
        self._users_with_api_keys = users_with_api_keys
        self._processing_statuses = processing_statuses
        self._entitlements = entitlements

    def entry_in_collection(self, entry_id: EntryId) -> bool:
        return entry_id in self._entries_in_collections

    def entry_user_ids(self, entry_id: EntryId) -> set[UserId]:
        user_ids: set[UserId] = set()

        for feed_id in self._feed_ids_by_entry.get(entry_id, set()):
            user_ids.update(self._user_ids_by_feed.get(feed_id, set()))

        return user_ids

    def users_have_api_keys(self, user_ids: Iterable[UserId]) -> bool:
        return any(user_id in self._users_with_api_keys for user_id in user_ids)

    def user_can_process_entry(self, user_id: UserId, entry_id: EntryId) -> bool:
        entry_age = self._entry_ages.get(entry_id)
        entry_age_limit = self._entry_age_limits.get(user_id)

        if entry_age is None or entry_age_limit is None:
            return False

        return entry_age_limit >= entry_age

    def user_entitlements(
        self,
        user_id: UserId,
    ) -> Mapping[EntitlementKindId, EffectiveEntitlementInterval | None]:
        return self._entitlements[user_id]

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
        if any(
            user_api_key_is_available(kind, api_key)
            for kind in _API_KEY_SETTING_KINDS
            if isinstance(api_key := settings.get(kind), str) and api_key
        )
    }


async def create_entries_cache(
    items: Sequence[EntryToProcess],
    processors: Sequence[ProcessorDispatchInfo],
    entitlement_kind_ids: Sequence[EntitlementKindId],
) -> EntriesCache:
    entry_ids = {item.entry_id for item in items}
    processor_ids = [processor.processor_id for processor in processors]
    entries_by_id, feed_ids_by_entry, processing_statuses = await asyncio.gather(
        l_domain.get_entries_by_ids(list(entry_ids)),
        _entry_feed_ids(entry_ids),
        operations.get_entries_processing_statuses(processor_ids, entry_ids),
    )
    entry_ages = {entry_id: entry.age_for_processing for entry_id, entry in entries_by_id.items() if entry is not None}
    entries_in_collections = _entry_ids_in_collections(feed_ids_by_entry)
    feed_ids = {feed_id for entry_feed_ids in feed_ids_by_entry.values() for feed_id in entry_feed_ids}
    user_ids_by_feed = await fl_domain.get_linked_users(feed_ids)
    user_ids = {user_id for feed_user_ids in user_ids_by_feed.values() for user_id in feed_user_ids}
    users_with_api_keys, entitlements, users_settings = await asyncio.gather(
        _users_with_api_keys(user_ids),
        e_domain.get_entitlements(
            list(user_ids),
            list(entitlement_kind_ids),
        ),
        us_domain.load_settings_for_users(
            user_ids,
            kinds=(_ENTRY_AGE_LIMIT_SETTING_KIND,),
        ),
    )
    entry_age_limits = {}

    for user_id, user_settings in users_settings.items():
        days = user_settings[_ENTRY_AGE_LIMIT_SETTING_KIND]
        assert isinstance(days, int)
        entry_age_limits[user_id] = datetime.timedelta(days=days)

    return EntriesCache(
        entry_ages=entry_ages,
        entry_age_limits=entry_age_limits,
        entries_in_collections=entries_in_collections,
        feed_ids_by_entry=feed_ids_by_entry,
        user_ids_by_feed=user_ids_by_feed,
        users_with_api_keys=users_with_api_keys,
        processing_statuses=processing_statuses,
        entitlements=entitlements,
    )
