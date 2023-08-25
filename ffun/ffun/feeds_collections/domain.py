from typing import Iterable

from ffun.feeds_collections.entities import Collection
from ffun.feeds_collections.predefines import predefines


def get_collections() -> Iterable[Collection]:
    return predefines.keys()


def get_feeds_for_collecton(collection: Collection) -> set[str]:
    return predefines[collection]
