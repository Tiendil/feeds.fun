import uuid

from ffun.core.postgresql import ExecuteType, run_in_transaction
from ffun.feeds_links import operations

add_link = operations.add_link
remove_link = operations.remove_link
get_linked_feeds = operations.get_linked_feeds
get_linked_users = operations.get_linked_users
has_linked_users = operations.has_linked_users


@run_in_transaction
async def tech_merge_feeds(execute: ExecuteType, from_feed_id: uuid.UUID, to_feed_id: uuid.UUID) -> None:
    await operations.tech_merge_feeds(execute, from_feed_id=from_feed_id, to_feed_id=to_feed_id)
