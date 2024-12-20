import uuid
from typing import NewType

UserId = NewType("UserId", uuid.UUID)
EntryId = NewType("EntryId", uuid.UUID)
FeedId = NewType("FeedId", uuid.UUID)
CollectionId = NewType("CollectionId", uuid.UUID)
SourceId = NewType("SourceId", uuid.UUID)
RuleId = NewType("RuleId", uuid.UUID)

# URL types for better normalization control in code
# conversion schemas:
# UnknownUrl -> AbsoluteUrl -> FeedUrl
# AbsoluteUrl + RelativeUrl -> AbsoluteUrl -> FeedUrl
UnknownUrl = NewType("UnknownUrl", str)  # URL from external source, we know nothing about it
AbsoluteUrl = NewType("AbsoluteUrl", str)  # Normalized and fixed absolute URL, always starts with scheme or //
RelativeUrl = NewType("RelativeUrl", str)  # not normalized relative URL
FeedUrl = NewType("FeedUrl", str)

UrlUid = NewType("UrlUid", str)  # uid that was built from URL
SourceUid = NewType("SourceUid", str)  # uid that was built from URL
