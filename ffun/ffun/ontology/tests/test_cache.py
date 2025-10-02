import time

import pytest
from pytest_mock import MockerFixture

from ffun.domain.entities import TagId, TagUid
from ffun.ontology.cache import TagsCache


class TestTagsCache:

    @pytest.fixture()
    def cache(self) -> TagsCache:
        return TagsCache()

    def test_initialize(self, cache: TagsCache) -> None:
        assert cache._cache == {}
        assert cache._cache.inverse == {}
        assert 0 < time.monotonic() - cache._last_reset_time < 1
        assert cache._reset_interval > 0

    @pytest.mark.asyncio
    async def test_ensure_cache_freshness(self, cache: TagsCache, three_tags_ids: tuple[TagId, TagId, TagId]) -> None:
        await cache.uids_by_ids(three_tags_ids)

        assert len(cache._cache) == 3

        cache._ensure_cache_freshness()

        assert len(cache._cache) == 3

        cache._last_reset_time = time.monotonic() - cache._reset_interval - 1.0

        cache._ensure_cache_freshness()

        assert len(cache._cache) == 0

    @pytest.mark.asyncio
    async def test_id_by_uid(self, cache: TagsCache) -> None:
        uid = TagUid("xxx-aaa")

        tag_id = await cache._id_by_uid(uid)

        assert uid in cache._cache
        assert tag_id in cache._cache.inverse

        tag_id_2 = await cache._id_by_uid(uid)

        assert tag_id == tag_id_2

    @pytest.mark.asyncio
    async def test_ids_by_uids(self, cache: TagsCache, mocker: MockerFixture) -> None:
        uids = [TagUid("xxx-aaa"), TagUid("yyy-bbb"), TagUid("zzz-ccc")]

        ensure_cache_freshness = mocker.patch.object(TagsCache, "_ensure_cache_freshness")

        ids = await cache.ids_by_uids(uids)

        assert len(ids) == 3

        for uid in uids:
            assert uid in ids
            assert uid in cache._cache
            assert ids[uid] in cache._cache.inverse

        ensure_cache_freshness.assert_called_once()

    @pytest.mark.asyncio
    async def test_uids_by_ids(
        self, cache: TagsCache, mocker: MockerFixture, three_tags_ids: tuple[TagId, TagId, TagId]
    ) -> None:
        ids = list(three_tags_ids)

        ensure_cache_freshness = mocker.patch.object(TagsCache, "_ensure_cache_freshness")

        uids = await cache.uids_by_ids(ids)

        assert len(uids) == 3

        for tag_id in ids:
            assert tag_id in uids
            assert uids[tag_id] in cache._cache
            assert tag_id in cache._cache.inverse

        ensure_cache_freshness.assert_called_once()
