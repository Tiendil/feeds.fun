from typing import Generic, TypeVar

from ffun.core import errors


class Entity:
    __slots__ = ("key",)

    def __init__(self, key: int) -> None:
        self.key = key


ENTITY = TypeVar("ENTITY", bound=Entity)


class Register(Generic[ENTITY]):
    __slots__ = ("_entities",)

    def __init__(self) -> None:
        self._entities: dict[int, ENTITY] = {}

    def add(self, entity: ENTITY) -> None:
        if entity.key in self._entities:
            raise errors.EntityAlreadyRegistered()

        self._entities[entity.key] = entity

    def get(self, key: int) -> ENTITY:
        return self._entities[key]

    def all(self) -> dict[int, ENTITY]:
        return dict(self._entities)
