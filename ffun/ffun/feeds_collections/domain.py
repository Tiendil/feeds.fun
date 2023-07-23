from typing import Iterable

from .entities import Collection
from .predefines import predefines


def get_collections() -> Iterable[Collection]:
    return predefines.keys()


def get_feeds_for_collecton(collection: Collection) -> set[str]:
    return predefines[collection]
