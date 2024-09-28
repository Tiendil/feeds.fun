import uuid
from typing import NewType

EntryId = NewType("EntryId", uuid.UUID)
FeedId = NewType("FeedId", uuid.UUID)
CollectionId = NewType("CollectionId", uuid.UUID)
SourceId = NewType("SourceId", uuid.UUID)
