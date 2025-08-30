from ffun.tags.entities import TagInNormalization


class Normalizer:
    __slots__ = ()

    async def normalize(self, tag: TagInNormalization) -> tuple[bool, list[TagInNormalization]]:
        raise NotImplementedError("Must be implemented in subclasses")
