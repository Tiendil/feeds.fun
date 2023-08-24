import asyncio
import random
import uuid

import pytest
from pytest_mock import MockerFixture

from ffun.core import utils
from ffun.core.postgresql import ExecuteType, execute, run_in_transaction
from ffun.feeds import domain as f_domain
from ffun.feeds import entities as f_entities
from ffun.feeds_links import domain as fl_domain
from ffun.parsers import entities as p_entities

from .. import errors
from ..domain import detect_orphaned, sync_feed_info


class TestDetectOrphaned:

    @pytest.mark.asyncio
    async def test_is_orphaned(self, saved_feed_id: uuid.UUID) -> None:
        assert await detect_orphaned(saved_feed_id)

        loaded_feed = await f_domain.get_feed(saved_feed_id)

        assert loaded_feed.state == f_entities.FeedState.orphaned

    @pytest.mark.asyncio
    async def test_not_orphaned(self, internal_user_id: uuid.UUID, saved_feed_id: uuid.UUID) -> None:
        await fl_domain.add_link(internal_user_id, saved_feed_id)

        assert not await detect_orphaned(saved_feed_id)

        loaded_feed = await f_domain.get_feed(saved_feed_id)

        assert loaded_feed.state != f_entities.FeedState.orphaned


class TestSyncFeedInfo:

    @pytest.mark.asyncio
    async def test_no_sync_required(self, saved_feed: f_entities.Feed, mocker: MockerFixture) -> None:
        update_feed_info = mocker.patch('ffun.feeds.domain.update_feed_info')

        feed_info = p_entities.FeedInfo(url=saved_feed.url,
                                        title=saved_feed.title,
                                        description=saved_feed.description,
                                        entries=[])

        await sync_feed_info(saved_feed, feed_info)

        update_feed_info.assert_not_called()

    @pytest.mark.asyncio
    async def test_sync_required(self, saved_feed: f_entities.Feed) -> None:
        feed_info = p_entities.FeedInfo(url=saved_feed.url,
                                        title=uuid.uuid4().hex,
                                        description=uuid.uuid4().hex,
                                        entries=[])

        await sync_feed_info(saved_feed, feed_info)

        loaded_feed = await f_domain.get_feed(saved_feed.id)

        assert loaded_feed.title == feed_info.title
        assert loaded_feed.description == feed_info.description
