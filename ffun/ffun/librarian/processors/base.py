from typing import Any

from ffun.librarian import errors
from ffun.library.entities import Entry
from ffun.ontology.entities import ProcessorTag


class Processor:
    __slots__ = ("_name",)

    def __init__(self, name: str):
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    async def process(self, entry: Entry) -> list[ProcessorTag]:
        raise NotImplementedError('You must implement "process" method in child class')


######################################
# Some processors for testing purposes
######################################


class AlwaysConstantProcessor(Processor):
    __slots__ = ("_tags",)

    def __init__(self, tags: list[str], **kwargs: Any):
        super().__init__(**kwargs)
        self._tags = tags

    async def process(self, entry: Entry) -> list[ProcessorTag]:
        return [ProcessorTag(raw_uid=tag) for tag in self._tags]


class AlwaysSkipEntryProcessor(Processor):
    async def process(self, entry: Entry) -> list[ProcessorTag]:
        raise errors.SkipEntryProcessing()


class AlwaysErrorProcessor(Processor):
    class CustomError(Exception):
        pass

    async def process(self, entry: Entry) -> list[ProcessorTag]:
        raise self.CustomError()
