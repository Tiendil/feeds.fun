import datetime

from ffun.core import utils

from . import operations

load_resources = operations.get_resources
try_to_reserve = operations.reserve
convert_reserved_to_used = operations.convert_reserved_to_used


def month_interval_start(now: datetime.datetime|None = None) -> datetime.datetime:
    if now is None:
        now = utils.now()

    return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
