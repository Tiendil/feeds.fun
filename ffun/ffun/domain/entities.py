import uuid

from typing import Any, NewType

EntryId = NewType("EntryId", uuid.UUID)
FeedId = NewType("FeedId", uuid.UUID)
CollectionId = NewType("CollectionId", uuid.UUID)
