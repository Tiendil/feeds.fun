import decimal
import enum
import uuid
from typing import NewType

from ffun.core.entities import BaseEntity, NonEmptyString


class SerializedId(NonEmptyString):
    __slots__ = ()


class BenefitId(NonEmptyString):
    __slots__ = ()


class ProviderId(NonEmptyString):
    __slots__ = ()


class ProviderAccountId(NonEmptyString):
    __slots__ = ()


class ProviderObjectId(NonEmptyString):
    __slots__ = ()


class ProviderObjectReference(BaseEntity):
    provider_id: ProviderId
    provider_account_id: ProviderAccountId
    provider_object_id: ProviderObjectId


class ProviderStatus(NonEmptyString):
    __slots__ = ()


class PurchasedStateSaveOutcome(enum.IntEnum):
    created = 1
    updated = 2
    refreshed = 3
    same = 4
    stale = 5


UserId = NewType("UserId", uuid.UUID)
BenefitTransactionId = NewType("BenefitTransactionId", uuid.UUID)
SubscriptionId = NewType("SubscriptionId", uuid.UUID)
OneTimePurchaseId = NewType("OneTimePurchaseId", uuid.UUID)
EntryId = NewType("EntryId", uuid.UUID)
FeedId = NewType("FeedId", uuid.UUID)
CollectionId = NewType("CollectionId", uuid.UUID)
CollectionSlug = NewType("CollectionSlug", str)
SourceId = NewType("SourceId", uuid.UUID)
RuleId = NewType("RuleId", uuid.UUID)
TagId = NewType("TagId", int)
TagUid = NewType("TagUid", str)
TagUidPart = NewType("TagUidPart", str)
IdPId = NewType("IdPId", int)  # Identity provider ID
ProcessorId = NewType("ProcessorId", int)
Days = NewType("Days", int)

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

USDCost = NewType("USDCost", decimal.Decimal)

LLMTokens = NewType("LLMTokens", int)
