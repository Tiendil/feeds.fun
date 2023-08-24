import asyncio
import random
import uuid

import pytest

from ffun.core import utils
from ffun.core.postgresql import ExecuteType, execute, run_in_transaction
from ffun.feeds import domain as f_domain
from ffun.feeds import entities as f_entities
from ffun.feeds_links import domain as fl_domain

from .. import errors
from ..domain import detect_orphaned


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
