import datetime
import uuid

from ffun.domain.domain import new_user_id
from ffun.domain.entities import (
    BenefitId,
    BenefitTransactionId,
    OneTimePurchaseId,
    ProviderAccountId,
    ProviderId,
    ProviderObjectId,
    ProviderObjectReference,
    ProviderStatus,
    UserId,
)
from ffun.one_time_purchases.entities import (
    Purchase,
    PurchaseStatus,
)


def make_provider_purchase_reference(
    *,
    provider_id: str = "test-provider",
    provider_account_id: str = "test-account",
    provider_object_id: str | None = None,
) -> ProviderObjectReference:
    return ProviderObjectReference(
        provider_id=ProviderId(provider_id),
        provider_account_id=ProviderAccountId(provider_account_id),
        provider_object_id=ProviderObjectId(provider_object_id or str(uuid.uuid4())),
    )


def make_purchase(  # noqa: CFQ002
    *,
    one_time_purchase_id: OneTimePurchaseId | None = None,
    state_transaction_id: BenefitTransactionId | None = None,
    user_id: UserId | None = None,
    benefit_id: BenefitId = BenefitId("test-benefit"),
    status: PurchaseStatus = PurchaseStatus.completed,
    provider_status: ProviderStatus = ProviderStatus("paid"),
    purchased_at: datetime.datetime | None = None,
    provider_updated_at: datetime.datetime | None = None,
) -> Purchase:
    now = datetime.datetime.now(tz=datetime.UTC)
    return Purchase(
        id=one_time_purchase_id or OneTimePurchaseId(uuid.uuid4()),
        state_transaction_id=state_transaction_id or BenefitTransactionId(uuid.uuid4()),
        user_id=user_id or new_user_id(),
        benefit_id=benefit_id,
        status=status,
        provider_status=provider_status,
        purchased_at=purchased_at or now - datetime.timedelta(days=1),
        provider_updated_at=provider_updated_at or now,
    )
