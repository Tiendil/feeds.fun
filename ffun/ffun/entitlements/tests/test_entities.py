import datetime
import uuid
from typing import cast

import pydantic
import pytest

from ffun.domain.datetime_intervals import LIFETIME_INTERVAL_END_MARKER
from ffun.domain.entities import BenefitTransactionId
from ffun.entitlements.entities import (
    ENTITLEMENT_KINDS,
    EntitlementGuarantee,
    EntitlementKindId,
    EntitlementSourceId,
    MergePolicy,
    SourceEntitlement,
)
from ffun.entitlements.tests.make import make_effective_entitlement_interval, make_source_entitlement
from ffun.subscriptions.domain import new_subscription_id


class TestEntitlementKindId:
    def test_values_are_stable(self) -> None:
        assert [(kind.name, kind.value) for kind in EntitlementKindId] == [
            ("day_tokens", 1),
            ("month_tokens", 2),
            ("lifetime_tokens", 3),
        ]


class TestMergePolicy:
    def test_values_are_stable(self) -> None:
        assert [(policy.name, policy.value) for policy in MergePolicy] == [
            ("max", "max"),
            ("min", "min"),
            ("sum", "sum"),
        ]


class TestEntitlementKinds:
    def test_registry_defines_every_kind_once(self) -> None:
        assert [kind.id for kind in ENTITLEMENT_KINDS] == list(EntitlementKindId)
        assert [kind.merge_policy for kind in ENTITLEMENT_KINDS] == [
            MergePolicy.max,
            MergePolicy.max,
            MergePolicy.sum,
        ]
        assert [kind.is_lifetime for kind in ENTITLEMENT_KINDS] == [False, False, True]


class TestEntitlementGuarantee:
    @pytest.mark.parametrize("value", [None, True, 1.5, "1"])
    def test_init__value_must_be_integer(self, value: object) -> None:
        with pytest.raises(pydantic.ValidationError, match="integer"):
            EntitlementGuarantee(kind_id=EntitlementKindId.day_tokens, value=cast(int, value))


class TestSourceEntitlement:
    @pytest.mark.parametrize("value", [None, True, 1.5, "1"])
    def test_init__grant_requires_integer_value(self, value: object) -> None:
        with pytest.raises(pydantic.ValidationError, match="integer"):
            make_source_entitlement(value=cast(int, value))

    @pytest.mark.parametrize(
        ("field_name", "message"),
        [
            ("starts_at", "activation timestamp must have a UTC offset"),
            ("expires_at", "expiration timestamp must have a UTC offset"),
            ("revoked_at", "revocation timestamp must have a UTC offset"),
        ],
    )
    def test_init__timestamps_require_utc_offset(self, field_name: str, message: str) -> None:
        now = datetime.datetime.now(tz=datetime.UTC)

        with pytest.raises(pydantic.ValidationError, match=message):
            make_source_entitlement(**{field_name: now.replace(tzinfo=None)})  # type: ignore[arg-type]

    def test_init__activation_must_be_before_expiration(self) -> None:
        now = datetime.datetime.now(tz=datetime.UTC)

        with pytest.raises(pydantic.ValidationError, match="activation timestamp must be earlier than expiration"):
            make_source_entitlement(starts_at=now, expires_at=now)

    @pytest.mark.parametrize(
        ("revoked_at", "revoked_by_transaction_id"),
        [
            (datetime.datetime.now(tz=datetime.UTC), None),
            (None, BenefitTransactionId(uuid.uuid4())),
        ],
    )
    def test_init__revocation_time_and_transaction_are_defined_together(
        self,
        revoked_at: datetime.datetime | None,
        revoked_by_transaction_id: BenefitTransactionId | None,
    ) -> None:
        values = cast(dict[str, object], make_source_entitlement().model_dump())
        values["revoked_at"] = revoked_at
        values["revoked_by_transaction_id"] = revoked_by_transaction_id

        with pytest.raises(pydantic.ValidationError, match="revocation time and transaction"):
            SourceEntitlement.model_validate(values)

    def test_granted__reflects_revocation_state(self) -> None:
        granted = make_source_entitlement()
        revoked = make_source_entitlement(revoked_at=datetime.datetime.now(tz=datetime.UTC))

        assert granted.granted
        assert not revoked.granted

    def test_validate_grant__recurring(self) -> None:
        make_source_entitlement(kind_id=EntitlementKindId.day_tokens).validate_grant(ENTITLEMENT_KINDS[0])

    def test_validate_grant__lifetime(self) -> None:
        make_source_entitlement(
            kind_id=EntitlementKindId.lifetime_tokens,
            expires_at=LIFETIME_INTERVAL_END_MARKER,
        ).validate_grant(ENTITLEMENT_KINDS[2])

    def test_validate_grant__requires_matching_kind(self) -> None:
        entitlement = make_source_entitlement(kind_id=EntitlementKindId.day_tokens)

        with pytest.raises(ValueError, match="kind must match"):
            entitlement.validate_grant(ENTITLEMENT_KINDS[1])

    def test_validate_grant__rejects_revoked_entitlement(self) -> None:
        entitlement = make_source_entitlement(revoked_at=datetime.datetime.now(tz=datetime.UTC))

        with pytest.raises(ValueError, match="grant must not be revoked"):
            entitlement.validate_grant(ENTITLEMENT_KINDS[0])

    def test_validate_grant__lifetime_requires_stable_expiration(self) -> None:
        now = datetime.datetime.now(tz=datetime.UTC)
        entitlement = make_source_entitlement(
            kind_id=EntitlementKindId.lifetime_tokens,
            starts_at=now,
            expires_at=now + datetime.timedelta(days=1),
        )

        with pytest.raises(ValueError, match="stable lifetime"):
            entitlement.validate_grant(ENTITLEMENT_KINDS[2])

    def test_validate_grant__recurring_rejects_lifetime_expiration(self) -> None:
        entitlement = make_source_entitlement(
            kind_id=EntitlementKindId.day_tokens,
            expires_at=LIFETIME_INTERVAL_END_MARKER,
        )

        with pytest.raises(ValueError, match="source-supplied"):
            entitlement.validate_grant(ENTITLEMENT_KINDS[0])

    def test_has_same_grant_as__ignores_revocation_state(self) -> None:
        entitlement = make_source_entitlement()
        revoked = entitlement.replace(
            revoked_at=datetime.datetime.now(tz=datetime.UTC),
            revoked_by_transaction_id=BenefitTransactionId(uuid.uuid4()),
        )

        assert entitlement.has_same_grant_as(revoked)

    @pytest.mark.parametrize(
        "field_name",
        [
            "source_id",
            "grant_transaction_id",
            "user_id",
            "subscription_id",
            "kind_id",
            "value",
            "starts_at",
            "expires_at",
        ],
    )
    def test_has_same_grant_as__detects_changed_immutable_field(self, field_name: str) -> None:
        entitlement = make_source_entitlement(value=10)
        changed_values: dict[str, object] = {
            "source_id": EntitlementSourceId("changed-source"),
            "grant_transaction_id": BenefitTransactionId(uuid.uuid4()),
            "user_id": make_source_entitlement().user_id,
            "subscription_id": new_subscription_id(),
            "kind_id": EntitlementKindId.month_tokens,
            "value": 20,
            "starts_at": entitlement.starts_at + datetime.timedelta(microseconds=1),
            "expires_at": entitlement.expires_at - datetime.timedelta(microseconds=1),
        }

        assert not entitlement.has_same_grant_as(entitlement.replace(**{field_name: changed_values[field_name]}))


class TestEffectiveEntitlementInterval:
    @pytest.mark.parametrize(
        ("field_name", "message"),
        [
            ("starts_at", "activation timestamp must have a UTC offset"),
            ("expires_at", "expiration timestamp must have a UTC offset"),
        ],
    )
    def test_init__timestamps_require_utc_offset(self, field_name: str, message: str) -> None:
        now = datetime.datetime.now(tz=datetime.UTC)

        with pytest.raises(pydantic.ValidationError, match=message):
            make_effective_entitlement_interval(**{field_name: now.replace(tzinfo=None)})  # type: ignore[arg-type]

    def test_init__activation_must_be_before_expiration(self) -> None:
        now = datetime.datetime.now(tz=datetime.UTC)

        with pytest.raises(pydantic.ValidationError, match="activation timestamp must be earlier than expiration"):
            make_effective_entitlement_interval(starts_at=now, expires_at=now)
