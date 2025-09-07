from ffun.core import logging, metrics
from ffun.ontology.entities import RawTag
from ffun.tags.entities import TagInNormalization
from ffun.tags.settings import settings

logger = logging.get_module_logger()


class Normalizer:
    __slots__ = ()

    async def normalize(self, tag: TagInNormalization) -> tuple[bool, list[RawTag]]:
        raise NotImplementedError("Must be implemented in subclasses")


class FakeNormalizer(Normalizer):
    slots__ = ("tag_valid", "new_tags")

    def __init__(self, tag_valid: bool, new_tags: list[RawTag]) -> None:
        self.tag_valid = tag_valid
        self.new_tags = new_tags

    async def normalize(self, tag: TagInNormalization) -> tuple[bool, list[RawTag]]:
        return self.tag_valid, self.new_tags


class NormalizerAlwaysError(Normalizer):
    slots__ = ("exception",)

    def __init__(self, exception: BaseException) -> None:
        self.exception = exception

    async def normalize(self, tag: TagInNormalization) -> tuple[bool, list[RawTag]]:
        raise self.exception


class NormalizerInfo:
    __slots__ = ("id", "name", "_normalizer", "metric_processed", "metric_consumed", "metric_produced")

    def __init__(self, id: int, name: str, normalizer: Normalizer) -> None:
        self.id = id
        self.name = name
        self._normalizer = normalizer

        self.metric_processed = metrics.Accumulator(
            interval=settings.metric_accumulation_interval, event="tag_normalizer_processed", normalizer_id=id
        )
        self.metric_consumed = metrics.Accumulator(
            interval=settings.metric_accumulation_interval, event="tag_normalizer_consumed", normalizer_id=id
        )
        self.metric_produced = metrics.Accumulator(
            interval=settings.metric_accumulation_interval, event="tag_normalizer_produced", normalizer_id=id
        )

    async def normalize(self, tag: TagInNormalization) -> tuple[bool, list[RawTag]]:
        try:
            tag_valid, new_tags = await self._normalizer.normalize(tag)

            self.metric_processed.measure(1)
            self.metric_consumed.measure(0 if tag_valid else 1)
            self.metric_produced.measure(len(new_tags))

        except BaseException:
            logger.exception("tag_normalizer_failed", normalizer_id=self.id, tag=tag.uid)
            # in case of failure, we behave like there was no such normalizer
            return True, []

        finally:
            self.metric_processed.flush_if_time()
            self.metric_consumed.flush_if_time()
            self.metric_produced.flush_if_time()

        return tag_valid, new_tags
