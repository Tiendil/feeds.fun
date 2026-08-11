import datetime
import uuid

from ffun.domain.domain import new_user_id
from ffun.domain.entities import UserId
from ffun.subscriptions.entities import (
    ProviderCustomerId,
    ProviderId,
    ProviderMerchantId,
    ProviderStatus,
    ProviderSubscriptionId,
    Subscription,
    SubscriptionStatusId,
)


def make_subscription(  # noqa: CFQ002
    *,
    provider_id: ProviderId = ProviderId("test-provider"),
    provider_merchant_id: ProviderMerchantId = ProviderMerchantId("test-merchant"),
    provider_subscription_id: ProviderSubscriptionId | None = None,
    user_id: UserId | None = None,
    provider_customer_id: ProviderCustomerId = ProviderCustomerId("customer-test"),
    status: SubscriptionStatusId = SubscriptionStatusId.active,
    provider_status: ProviderStatus = ProviderStatus("active"),
    started_at: datetime.datetime | None = None,
    renews_at: datetime.datetime | None = None,
    ends_at: datetime.datetime | None = None,
    provider_updated_at: datetime.datetime | None = None,
) -> Subscription:
    now = datetime.datetime.now(tz=datetime.UTC)
    return Subscription(
        provider_id=provider_id,
        provider_merchant_id=provider_merchant_id,
        provider_subscription_id=provider_subscription_id or ProviderSubscriptionId(f"subscription-{uuid.uuid4()}"),
        user_id=user_id or new_user_id(),
        provider_customer_id=provider_customer_id,
        status=status,
        provider_status=provider_status,
        started_at=started_at or now - datetime.timedelta(days=30),
        renews_at=renews_at,
        ends_at=ends_at,
        provider_updated_at=provider_updated_at or now,
    )
