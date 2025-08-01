import datetime

from ffun.core import logging, utils

logger = logging.get_module_logger()


class Accumulator:
    __slots__ = ("interval", "event", "attributes", "_last_measure_at", "_count", "_sum")

    def __init__(self, interval: datetime.timedelta, event: str, **attributes: logging.LabelValue):
        self.interval = interval
        self.event = event
        self.attributes = attributes
        self._last_measure_at: datetime.datetime | None = None
        self._count = 0
        self._sum = 0

    @property
    def count(self) -> int:
        return self._count

    @property
    def sum(self) -> int:
        return self._sum

    def measure(self, value: int) -> None:
        if self._last_measure_at is None:
            self._last_measure_at = utils.now()

        self._count += 1
        self._sum += value

    def flush_if_time(self) -> None:
        if self._last_measure_at is None:
            return

        if utils.now() - self._last_measure_at < self.interval:
            return

        logger.business_slice(self.event, user_id=None, count=self._count, sum=self._sum, **self.attributes)

        self._last_measure_at = None
        self._count = 0
        self._sum = 0
