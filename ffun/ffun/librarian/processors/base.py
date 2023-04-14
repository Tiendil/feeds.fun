from ffun.library.entities import Entry


class Processor:
    __slots__ = ('_name',)

    def __init__(self, name: str):
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    async def process(self, entry: Entry) -> set[str]:
        raise NotImplementedError
