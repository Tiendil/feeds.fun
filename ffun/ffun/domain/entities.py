import uuid
from typing import NewType

UserId = NewType("UserId", uuid.UUID)
EntryId = NewType("EntryId", uuid.UUID)
FeedId = NewType("FeedId", uuid.UUID)
CollectionId = NewType("CollectionId", uuid.UUID)
SourceId = NewType("SourceId", uuid.UUID)


UnknownUrl = NewType("UnknownUrl", str)  # URL from external source, we know nothing about it
AbsoluteUrl = NewType("AbsoluteUrl", str)  # Normalized and fixed absolute URL, always starts with scheme or //
RelativeUrl = NewType("RelativeUrl", str)  # not normalized relative URL

UrlUid = NewType("UrlUid", str)  # uid that was built from URL
SourceUid = NewType("SourceUid", str)  # uid that was built from URL
