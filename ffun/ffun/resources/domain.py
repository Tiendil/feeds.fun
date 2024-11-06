import datetime

from ffun.domain.entities import UserId
from ffun.resources import operations
from ffun.resources.entities import Resource

load_resources = operations.load_resources
try_to_reserve = operations.try_to_reserve
convert_reserved_to_used = operations.convert_reserved_to_used
load_resource_history = operations.load_resource_history
count_total_resources_per_user = operations.count_total_resources_per_user


async def load_resource(user_id: UserId, kind: int, interval_started_at: datetime.datetime) -> Resource:
    resources = await load_resources([user_id], kind, interval_started_at)
    return resources[user_id]
