import datetime
import uuid

from ffun.core import utils
from ffun.resources import operations
from ffun.resources.entities import Resource

load_resources = operations.load_resources
try_to_reserve = operations.try_to_reserve
convert_reserved_to_used = operations.convert_reserved_to_used
load_resource_history = operations.load_resource_history


def month_interval_start(now: datetime.datetime | None = None) -> datetime.datetime:
    if now is None:
        now = utils.now()

    return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


async def load_resource(user_id: uuid.UUID, kind: int, interval_started_at: datetime.datetime) -> Resource:
    resources = await load_resources([user_id], kind, interval_started_at)
    return resources[user_id]
