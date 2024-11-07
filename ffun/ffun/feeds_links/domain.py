from typing import Iterable

from ffun.core.postgresql import ExecuteType, run_in_transaction
from ffun.domain.entities import UserId
from ffun.feeds.entities import FeedId
from ffun.feeds_links import operations

add_link = operations.add_link
remove_link = operations.remove_link
get_link = operations.get_link
get_linked_feeds = operations.get_linked_feeds
get_linked_users = operations.get_linked_users
has_linked_users = operations.has_linked_users
count_feeds_per_user = operations.count_feeds_per_user
count_subset_feeds_per_user = operations.count_subset_feeds_per_user


async def get_linked_users_flat(feed_ids: Iterable[FeedId]) -> set[UserId]:
    users = await operations.get_linked_users(feed_ids)

    answer = set()

    for user_set in users.values():
        answer.update(user_set)

    return answer


@run_in_transaction
async def tech_merge_feeds(execute: ExecuteType, from_feed_id: FeedId, to_feed_id: FeedId) -> None:
    await operations.tech_merge_feeds(execute, from_feed_id=from_feed_id, to_feed_id=to_feed_id)
