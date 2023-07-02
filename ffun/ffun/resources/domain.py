import datetime

from ffun.core import utils

from . import operations

load_resources = operations.get_resources
try_to_reserve = operations.reserve


def month_interval_start(now: datetime.datetime|None = None) -> datetime.datetime:
    if now is None:
        now = utils.now()

    return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
