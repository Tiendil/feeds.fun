import time
from typing import Iterable

from bidict import bidict

from ffun.domain.entities import TagId, TagUid
from ffun.ontology import operations
from ffun.ontology.settings import settings


# We cache tags in local process memory to speed up processing of user requests
# Since we periodically remove orphaned tags, we must somehow update all caches in all processes
# That can be done in multiple ways, however, for now we just use simplest possible approach:
# reset cache once in a while.
# We may want to implement more sophisticated approach in the future.
class TagsCache:
    __slots__ = ("_cache", "_last_reset_time", "_reset_interval")

    def __init__(self) -> None:
        self._cache: bidict[TagUid, TagId] = bidict()
        self._last_reset_time = time.monotonic()
        self._reset_interval = settings.tags_cache_reset_interval.total_seconds()

    def _ensure_cache_freshness(self) -> None:
        current_time = time.monotonic()

        if current_time < self._reset_interval + self._last_reset_time:
            return

        self._cache.clear()
        self._last_reset_time = current_time

    async def _id_by_uid(self, tag: TagUid) -> TagId:
        if tag in self._cache:
            return self._cache[tag]

        tag_id = await operations.get_or_create_id_by_tag(tag)

        self._cache[tag] = tag_id

        return tag_id

    async def ids_by_uids(self, tags: Iterable[TagUid]) -> dict[TagUid, TagId]:
        self._ensure_cache_freshness()

        return {tag: await self._id_by_uid(tag) for tag in tags}

    async def uids_by_ids(self, ids: Iterable[TagId]) -> dict[TagId, TagUid]:
        self._ensure_cache_freshness()

        result = {}

        tags_to_request = []

        for tag_id in ids:
            if tag_id in self._cache.inverse:
                result[tag_id] = self._cache.inverse[tag_id]
            else:
                tags_to_request.append(tag_id)

        if not tags_to_request:
            return result

        missed_tags = await operations.get_tags_by_ids(tags_to_request)

        self._cache.inverse.update(missed_tags)

        result.update(missed_tags)

        return result
