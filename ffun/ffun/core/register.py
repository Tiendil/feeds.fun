from typing import Any

from . import errors


class Entity:
    __slots__ = ('key',)

    def __init__(self, key: int) -> None:
        self.key = key


class Register:
    __slots__ = ('_entities',)

    def __init__(self) -> None:
        self._entities = {}

    def add(self, entity) -> None:
        if entity.key in self._entities:
            raise errors.EntityAlreadyRegistered()

        self._entities[entity.key] = entity

    def get(self, key) -> Any:
        return self._entities.get(key)

    def all(self) -> dict[Any, Any]:
        return dict(self._entities)
