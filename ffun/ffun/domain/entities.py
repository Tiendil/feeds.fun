import uuid
from typing import NewType

UserId = NewType("UserId", uuid.UUID)
EntryId = NewType("EntryId", uuid.UUID)
FeedId = NewType("FeedId", uuid.UUID)
CollectionId = NewType("CollectionId", uuid.UUID)
SourceId = NewType("SourceId", uuid.UUID)


UnknowUrl = NewType("UnknowURL", str)  # URL from external source, we know nothing about it
AbsoluteUrl = NewType("AbsoluteURL", str)  # Normalized and fixed absolute URL, always starts with scheme or //
RelativeUrl = NewType("RelativeURL", str)  # not normalized relative URL

UrlUid = NewType("UidURL", str)  # uid that was built from URL
SourceUid = NewType("UidSource", str)  # uid that was built from URL
