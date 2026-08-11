import datetime
from decimal import Decimal
from typing import cast

import pydantic
import pytest

from ffun.api.spa.entities import (
    EntitlementKind,
    Feed,
    FeedInfo,
    Marker,
    MutableMarker,
    ProductStateEntitlement,
    ProductStateSubscription,
    ProductStateToken,
    RemoveMarkerRequest,
    ResourceKind,
    ResourceStatisticsInterval,
    ResourceStatisticsSeries,
    SetMarkerRequest,
    SubscriptionStatus,
    TokenKind,
)
from ffun.core import utils
from ffun.domain.domain import new_entry_id, new_user_id
from ffun.domain.urls import str_to_absolute_url, str_to_feed_url, url_to_uid
from ffun.entitlements.entities import EntitlementKindId
from ffun.entitlements.tests.make import make_effective_entitlement_interval
from ffun.feeds.entities import Feed as InternalFeed
from ffun.feeds.entities import FeedError
from ffun.parsers import entities as p_entities
from ffun.product.entities import Credit, Resource
from ffun.resources import entities as r_entities
from ffun.subscriptions.entities import SubscriptionStatusId
from ffun.subscriptions.tests.make import make_subscription


class TestFeed:
    def test_from_internal__default_entries_metrics_details(self, loaded_feed: InternalFeed) -> None:
        external_feed = Feed.from_internal(
            loaded_feed,
            linked_at=None,
            collection_ids=[],
            young=True,
            entries_per_day=0,
        )

        assert external_feed.young
        assert external_feed.entriesLoadedDetails is None
        assert external_feed.siteUrl is None

    @pytest.mark.asyncio
    async def test_from_internal__with_entries_metrics(self, loaded_feed: InternalFeed) -> None:
        linked_at = utils.now()
        site_url = str_to_absolute_url("https://example.com")

        external_feed = Feed.from_internal(
            loaded_feed.replace(site_url=site_url),
            linked_at=linked_at,
            collection_ids=[],
            young=False,
            entries_per_day=3,
            entries_loaded_details=[0, 1, 2],
        )

        assert external_feed.linkedAt == linked_at
        assert external_feed.siteUrl == site_url
        assert not external_feed.young
        assert external_feed.entriesPerDay == 3
        assert external_feed.entriesLoadedDetails == [0, 1, 2]

    def test_from_internal__with_last_error(self, loaded_feed: InternalFeed) -> None:
        error = FeedError.network_connection_timeout
        failed_feed = loaded_feed.replace(last_error=error)

        external_feed = Feed.from_internal(
            failed_feed,
            linked_at=None,
            collection_ids=[],
            young=True,
            entries_per_day=0,
        )

        assert external_feed.lastError == error.name


class TestFeedInfo:
    def test_from_internal__keeps_site_url(self) -> None:
        feed_url = str_to_feed_url("https://example.com/feed")
        site_url = str_to_absolute_url("https://example.com")

        external_feed = FeedInfo.from_internal(
            p_entities.FeedInfo(
                url=feed_url,
                site_url=site_url,
                title="Example",
                description="Example feed",
                uid=url_to_uid(feed_url),
                entries=[],
            ),
            is_linked=True,
        )

        assert external_feed.siteUrl == site_url
        assert external_feed.isLinked

    def test_from_internal__keeps_missing_site_url(self) -> None:
        feed_url = str_to_feed_url("https://example.com/feed")

        external_feed = FeedInfo.from_internal(
            p_entities.FeedInfo(
                url=feed_url,
                site_url=None,
                title="Example",
                description="Example feed",
                uid=url_to_uid(feed_url),
                entries=[],
            ),
            is_linked=False,
        )

        assert external_feed.siteUrl is None


class TestSetMarkerRequest:
    def test_accepts_mutable_marker(self) -> None:
        request = SetMarkerRequest(entryId=new_entry_id(), marker=MutableMarker.read)

        assert request.marker.to_internal().value == Marker.read

    def test_rejects_return_only_marker(self) -> None:
        payload: dict[str, object] = {"entryId": new_entry_id(), "marker": Marker.can_see_tags}

        with pytest.raises(pydantic.ValidationError):
            SetMarkerRequest.model_validate(payload)


class TestRemoveMarkerRequest:
    def test_accepts_mutable_marker(self) -> None:
        request = RemoveMarkerRequest(entryId=new_entry_id(), marker=MutableMarker.read)

        assert request.marker.to_internal().value == Marker.read

    def test_rejects_return_only_marker(self) -> None:
        payload: dict[str, object] = {"entryId": new_entry_id(), "marker": Marker.can_see_tags}

        with pytest.raises(pydantic.ValidationError):
            RemoveMarkerRequest.model_validate(payload)


class TestEntitlementKind:
    @pytest.mark.parametrize(
        "kind, internal_kind",
        [
            (EntitlementKind.day_tokens, EntitlementKindId.day_tokens),
            (EntitlementKind.month_tokens, EntitlementKindId.month_tokens),
            (EntitlementKind.lifetime_tokens, EntitlementKindId.lifetime_tokens),
        ],
    )
    def test_to_internal__supported_kinds(self, kind: EntitlementKind, internal_kind: EntitlementKindId) -> None:
        assert kind.to_internal() == internal_kind

    @pytest.mark.parametrize(
        "kind, internal_kind",
        [
            (EntitlementKind.day_tokens, EntitlementKindId.day_tokens),
            (EntitlementKind.month_tokens, EntitlementKindId.month_tokens),
            (EntitlementKind.lifetime_tokens, EntitlementKindId.lifetime_tokens),
        ],
    )
    def test_from_internal__supported_kinds(self, kind: EntitlementKind, internal_kind: EntitlementKindId) -> None:
        assert EntitlementKind.from_internal(internal_kind) == kind


class TestProductStateEntitlement:
    def test_from_internal__not_granted(self) -> None:
        assert ProductStateEntitlement.from_internal(None) == ProductStateEntitlement(
            granted=False,
            value=None,
            startsAt=None,
            expiresAt=None,
        )

    def test_from_internal__periodic(self) -> None:
        entitlement = make_effective_entitlement_interval(kind_id=EntitlementKindId.day_tokens)

        assert ProductStateEntitlement.from_internal(entitlement) == ProductStateEntitlement(
            granted=True,
            value=entitlement.value,
            startsAt=entitlement.starts_at,
            expiresAt=entitlement.expires_at,
        )

    def test_from_internal__lifetime(self) -> None:
        entitlement = make_effective_entitlement_interval(kind_id=EntitlementKindId.lifetime_tokens)

        assert ProductStateEntitlement.from_internal(entitlement) == ProductStateEntitlement(
            granted=True,
            value=entitlement.value,
            startsAt=entitlement.starts_at,
            expiresAt=None,
        )


class TestSubscriptionStatus:
    @pytest.mark.parametrize(
        "status, internal_status",
        [(SubscriptionStatus[status.name], status) for status in SubscriptionStatusId],
    )
    def test_from_internal__supported_statuses(
        self,
        status: SubscriptionStatus,
        internal_status: SubscriptionStatusId,
    ) -> None:
        assert SubscriptionStatus.from_internal(internal_status) == status


class TestProductStateSubscription:
    def test_from_internal__user_facing_fields(self) -> None:
        now = utils.now()
        started_at = now - datetime.timedelta(days=30)
        renews_at = now + datetime.timedelta(days=1)
        ends_at = now + datetime.timedelta(days=31)
        subscription = make_subscription(
            status=SubscriptionStatusId.past_due,
            started_at=started_at,
            renews_at=renews_at,
            ends_at=ends_at,
        )

        serialized = cast(dict[str, object], ProductStateSubscription.from_internal(subscription).model_dump())

        assert serialized == {
            "status": SubscriptionStatus.past_due,
            "startedAt": started_at,
            "renewsAt": renews_at,
            "endsAt": ends_at,
        }


class TestProductStateToken:
    def test_from_internal__no_entitlement(self) -> None:
        resource = r_entities.Resource(
            user_id=new_user_id(),
            kind=Resource.day_token_usage,
            interval_started_at=utils.now(),
            used=3,
            reserved=2,
        )

        assert ProductStateToken.from_internal(
            entitlement=None,
            resource=resource,
            period_started_at=None,
            period_ends_at=None,
        ) == ProductStateToken(
            limit=None,
            balance=0,
            periodStartsAt=None,
            periodEndsAt=None,
        )

    def test_from_internal__periodic(self) -> None:
        period_started_at = utils.now()
        period_ends_at = period_started_at + datetime.timedelta(days=1)
        entitlement = make_effective_entitlement_interval(kind_id=EntitlementKindId.day_tokens, value=10)
        resource = r_entities.Resource(
            user_id=entitlement.user_id,
            kind=Resource.day_token_usage,
            interval_started_at=period_started_at,
            used=3,
            reserved=2,
        )

        assert ProductStateToken.from_internal(
            entitlement=entitlement,
            resource=resource,
            period_started_at=period_started_at,
            period_ends_at=period_ends_at,
        ) == ProductStateToken(
            limit=10,
            balance=5,
            periodStartsAt=period_started_at,
            periodEndsAt=period_ends_at,
        )

    def test_from_internal__over_consumed(self) -> None:
        period_started_at = utils.now()
        period_ends_at = period_started_at + datetime.timedelta(days=1)
        entitlement = make_effective_entitlement_interval(kind_id=EntitlementKindId.day_tokens, value=10)
        resource = r_entities.Resource(
            user_id=entitlement.user_id,
            kind=Resource.day_token_usage,
            interval_started_at=period_started_at,
            used=8,
            reserved=3,
        )

        assert ProductStateToken.from_internal(
            entitlement=entitlement,
            resource=resource,
            period_started_at=period_started_at,
            period_ends_at=period_ends_at,
        ) == ProductStateToken(
            limit=10,
            balance=0,
            periodStartsAt=period_started_at,
            periodEndsAt=period_ends_at,
        )

    def test_from_internal__lifetime(self) -> None:
        entitlement = make_effective_entitlement_interval(kind_id=EntitlementKindId.lifetime_tokens, value=10)
        resource = r_entities.Resource(
            user_id=entitlement.user_id,
            kind=Resource.lifetime_token_usage,
            interval_started_at=utils.now(),
            used=3,
            reserved=2,
        )

        assert ProductStateToken.from_internal(
            entitlement=entitlement,
            resource=resource,
            period_started_at=None,
            period_ends_at=None,
        ) == ProductStateToken(
            limit=None,
            balance=5,
            periodStartsAt=None,
            periodEndsAt=None,
        )


class TestTokenKind:
    @pytest.mark.parametrize(
        "kind, internal_kind",
        [
            (TokenKind.day, Credit.day),
            (TokenKind.month, Credit.month),
            (TokenKind.lifetime, Credit.lifetime),
        ],
    )
    def test_from_internal__supported_kinds(self, kind: TokenKind, internal_kind: Credit) -> None:
        assert TokenKind.from_internal(internal_kind) == kind


class TestResourceKind:
    @pytest.mark.parametrize(
        "kind, internal_kind",
        [
            (ResourceKind.tokens_cost, Resource.tokens_cost),
            (ResourceKind.day_token_usage, Resource.day_token_usage),
            (ResourceKind.month_token_usage, Resource.month_token_usage),
            (ResourceKind.lifetime_token_usage, Resource.lifetime_token_usage),
        ],
    )
    def test_to_internal__resource_kind(self, kind: ResourceKind, internal_kind: Resource) -> None:
        assert kind.to_internal() == r_entities.ResourceKind(internal_kind)

    @pytest.mark.parametrize(
        "kind, internal_kind",
        [
            (ResourceKind.tokens_cost, Resource.tokens_cost),
            (ResourceKind.day_token_usage, Resource.day_token_usage),
            (ResourceKind.month_token_usage, Resource.month_token_usage),
            (ResourceKind.lifetime_token_usage, Resource.lifetime_token_usage),
        ],
    )
    def test_from_internal__resource_kind(self, kind: ResourceKind, internal_kind: Resource) -> None:
        assert ResourceKind.from_internal(internal_kind) == kind

    def test_from_internal__unsupported_value(self) -> None:
        with pytest.raises(ValueError):
            ResourceKind.from_internal(0)

    def test_amount_from_internal__token_usage(self) -> None:
        assert ResourceKind.lifetime_token_usage.amount_from_internal(13) == Decimal(13)

    def test_amount_from_internal__tokens_cost(self) -> None:
        assert ResourceKind.tokens_cost.amount_from_internal(1_500_000_000) == Decimal("1.5")


class TestResourceStatisticsInterval:
    @pytest.mark.parametrize(
        "interval",
        [
            ResourceStatisticsInterval.day,
            ResourceStatisticsInterval.month,
            ResourceStatisticsInterval.year,
        ],
    )
    def test_to_internal__interval(self, interval: ResourceStatisticsInterval) -> None:
        assert interval.to_internal() == r_entities.ResourceStatisticsInterval(interval.value)


class TestResourceStatisticsSeries:
    def test_from_internal__empty_values(self) -> None:
        first_date = utils.now().date()
        series = ResourceStatisticsSeries.from_internal(
            kind=ResourceKind.lifetime_token_usage,
            series=r_entities.ResourceStatisticsSeries(first_date=first_date, values=()),
        )

        assert series.firstDate == first_date
        assert series.values == []

    def test_from_internal__zero(self) -> None:
        first_date = utils.now().date()
        series = ResourceStatisticsSeries.from_internal(
            kind=ResourceKind.lifetime_token_usage,
            series=r_entities.ResourceStatisticsSeries(first_date=first_date, values=(0,)),
        )

        assert series.firstDate == first_date
        assert series.values == [Decimal(0)]

    def test_from_internal__converts_values(self) -> None:
        kind = ResourceKind.lifetime_token_usage
        first_date = utils.now().date()

        series = ResourceStatisticsSeries.from_internal(
            kind=kind,
            series=r_entities.ResourceStatisticsSeries(
                first_date=first_date,
                values=(2, 0, 4),
            ),
        )

        assert series.firstDate == first_date
        assert series.values == [Decimal(2), Decimal(0), Decimal(4)]
