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
