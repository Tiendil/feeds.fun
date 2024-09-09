from typing import Generic, TypeVar

from ffun.core import errors

KEY = int | str


class Entity:
    __slots__ = ("key",)

    # TODO: refactor to correct type inference
    def __init__(self, key: KEY) -> None:
        self.key = key


ENTITY = TypeVar("ENTITY", bound=Entity)


class Register(Generic[ENTITY]):
    __slots__ = ("_entities",)

    def __init__(self) -> None:
        self._entities: dict[KEY, ENTITY] = {}

    def add(self, entity: ENTITY) -> None:
        if entity.key in self._entities:
            raise errors.EntityAlreadyRegistered()

        self._entities[entity.key] = entity

    def get(self, key: KEY) -> ENTITY:
        return self._entities[key]

    def has(self, key: KEY) -> bool:
        return key in self._entities

    def remove(self, key: KEY) -> None:
        del self._entities[key]

    def all(self) -> dict[KEY, ENTITY]:
        return dict(self._entities)
