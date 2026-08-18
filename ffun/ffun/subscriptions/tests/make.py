import datetime
import uuid

from ffun.domain.domain import new_user_id
from ffun.domain.entities import BenefitId, BenefitTransactionId, SubscriptionId, UserId
from ffun.subscriptions.entities import (
    ProviderStatus,
    Subscription,
    SubscriptionStatusId,
)


def make_subscription(  # noqa: CFQ002
    *,
    subscription_id: SubscriptionId | None = None,
    state_transaction_id: BenefitTransactionId | None = None,
    user_id: UserId | None = None,
    benefit_id: BenefitId = BenefitId("test-benefit"),
    status: SubscriptionStatusId = SubscriptionStatusId.active,
    provider_status: ProviderStatus = ProviderStatus("active"),
    started_at: datetime.datetime | None = None,
    renews_at: datetime.datetime | None = None,
    ends_at: datetime.datetime | None = None,
    provider_updated_at: datetime.datetime | None = None,
) -> Subscription:
    now = datetime.datetime.now(tz=datetime.UTC)
    return Subscription(
        id=subscription_id or SubscriptionId(uuid.uuid4()),
        state_transaction_id=state_transaction_id or BenefitTransactionId(uuid.uuid4()),
        user_id=user_id or new_user_id(),
        benefit_id=benefit_id,
        status=status,
        provider_status=provider_status,
        started_at=started_at or now - datetime.timedelta(days=30),
        renews_at=renews_at,
        ends_at=ends_at,
        provider_updated_at=provider_updated_at or now,
    )
