import datetime
from typing import cast

import pydantic
import pytest

from ffun.entitlements.entities import (
    ENTITLEMENT_KINDS,
    LIFETIME_ENTITLEMENT_EXPIRES_AT,
    EntitlementKindId,
    EntitlementSourceId,
    EntitlementTransactionId,
    MergePolicy,
    SourceEntitlement,
)
from ffun.entitlements.tests.make import make_effective_entitlement_interval, make_source_entitlement


class TestEntitlementKinds:
    def test_registry_defines_every_kind_once(self) -> None:
        assert [kind.id for kind in ENTITLEMENT_KINDS] == list(EntitlementKindId)
        assert [kind.merge_policy for kind in ENTITLEMENT_KINDS] == [
            MergePolicy.max,
            MergePolicy.max,
            MergePolicy.sum,
        ]
        assert [kind.is_lifetime for kind in ENTITLEMENT_KINDS] == [False, False, True]

    def test_lifetime_expiration_is_stable_aware_future_timestamp(self) -> None:
        assert LIFETIME_ENTITLEMENT_EXPIRES_AT == datetime.datetime(
            year=9999,
            month=12,
            day=31,
            hour=23,
            minute=59,
            second=59,
            microsecond=999999,
            tzinfo=datetime.UTC,
        )


class TestSourceEntitlement:
    @pytest.mark.parametrize("source", ["", " "])
    def test_init__source_must_not_be_empty(self, source: str) -> None:
        values = cast(dict[str, object], make_source_entitlement().model_dump())
        values["source"] = source

        with pytest.raises(pydantic.ValidationError, match="EntitlementSourceId must not be empty"):
            SourceEntitlement.model_validate(values)

    @pytest.mark.parametrize("transaction_id", ["", " "])
    def test_init__transaction_id_must_not_be_empty(self, transaction_id: str) -> None:
        values = cast(dict[str, object], make_source_entitlement().model_dump())
        values["transaction_id"] = transaction_id

        with pytest.raises(pydantic.ValidationError, match="EntitlementTransactionId must not be empty"):
            SourceEntitlement.model_validate(values)

    @pytest.mark.parametrize("value", [None, True])
    def test_init__grant_requires_integer_value(self, value: object) -> None:
        with pytest.raises(pydantic.ValidationError, match="integer"):
            make_source_entitlement(value=cast(int, value))

    def test_init__activation_requires_utc_offset(self) -> None:
        now = datetime.datetime.now(tz=datetime.UTC)

        with pytest.raises(pydantic.ValidationError, match="activation timestamp must have a UTC offset"):
            make_source_entitlement(starts_at=now.replace(tzinfo=None))

    def test_init__expiration_requires_utc_offset(self) -> None:
        now = datetime.datetime.now(tz=datetime.UTC)

        with pytest.raises(pydantic.ValidationError, match="expiration timestamp must have a UTC offset"):
            make_source_entitlement(expires_at=now.replace(tzinfo=None))

    def test_init__revocation_requires_utc_offset(self) -> None:
        now = datetime.datetime.now(tz=datetime.UTC)

        with pytest.raises(pydantic.ValidationError, match="revocation timestamp must have a UTC offset"):
            make_source_entitlement(revoked_at=now.replace(tzinfo=None))

    def test_init__activation_must_be_before_expiration(self) -> None:
        now = datetime.datetime.now(tz=datetime.UTC)

        with pytest.raises(pydantic.ValidationError, match="activation timestamp must be earlier than expiration"):
            make_source_entitlement(starts_at=now, expires_at=now)

    def test_validate_grant__recurring(self) -> None:
        entitlement = make_source_entitlement(kind_id=EntitlementKindId.day_tokens)

        entitlement.validate_grant(ENTITLEMENT_KINDS[0])

    def test_validate_grant__lifetime(self) -> None:
        entitlement = make_source_entitlement(
            kind_id=EntitlementKindId.lifetime_tokens,
            expires_at=LIFETIME_ENTITLEMENT_EXPIRES_AT,
        )

        entitlement.validate_grant(ENTITLEMENT_KINDS[2])

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
            expires_at=LIFETIME_ENTITLEMENT_EXPIRES_AT,
        )

        with pytest.raises(ValueError, match="source-supplied"):
            entitlement.validate_grant(ENTITLEMENT_KINDS[0])

    def test_has_same_grant_as__ignores_revocation_state(self) -> None:
        entitlement = make_source_entitlement()
        revoked = entitlement.to_revoked(revoked_at=datetime.datetime.now(tz=datetime.UTC))

        assert entitlement.has_same_grant_as(revoked)

    @pytest.mark.parametrize(
        "field",
        ["source", "transaction_id", "user_id", "kind_id", "value", "starts_at", "expires_at"],
    )
    def test_has_same_grant_as__detects_changed_immutable_field(self, field: str) -> None:
        entitlement = make_source_entitlement(value=10)
        changed_values: dict[str, object] = {
            "source": EntitlementSourceId("changed-source"),
            "transaction_id": EntitlementTransactionId("changed-transaction"),
            "user_id": make_source_entitlement().user_id,
            "kind_id": EntitlementKindId.month_tokens,
            "value": 20,
            "starts_at": entitlement.starts_at + datetime.timedelta(microseconds=1),
            "expires_at": entitlement.expires_at - datetime.timedelta(microseconds=1),
        }

        assert not entitlement.has_same_grant_as(entitlement.replace(**{field: changed_values[field]}))

    def test_to_revoked__changes_only_revocation(self) -> None:
        entitlement = make_source_entitlement()
        revoked_at = datetime.datetime.now(tz=datetime.UTC)

        revoked = entitlement.to_revoked(revoked_at=revoked_at)

        assert revoked == make_source_entitlement(
            source=entitlement.source,
            transaction_id=entitlement.transaction_id,
            user_id=entitlement.user_id,
            kind_id=entitlement.kind_id,
            value=entitlement.value,
            starts_at=entitlement.starts_at,
            expires_at=entitlement.expires_at,
            revoked_at=revoked_at,
        )
        assert entitlement.granted
        assert not revoked.granted

    def test_to_revoked__validates_timestamp(self) -> None:
        entitlement = make_source_entitlement()

        with pytest.raises(pydantic.ValidationError, match="revocation timestamp must have a UTC offset"):
            entitlement.to_revoked(revoked_at=datetime.datetime.now())


class TestEffectiveEntitlementInterval:
    def test_init__activation_requires_utc_offset(self) -> None:
        now = datetime.datetime.now(tz=datetime.UTC)

        with pytest.raises(pydantic.ValidationError, match="activation timestamp must have a UTC offset"):
            make_effective_entitlement_interval(starts_at=now.replace(tzinfo=None))

    def test_init__expiration_requires_utc_offset(self) -> None:
        now = datetime.datetime.now(tz=datetime.UTC)

        with pytest.raises(pydantic.ValidationError, match="expiration timestamp must have a UTC offset"):
            make_effective_entitlement_interval(expires_at=now.replace(tzinfo=None))

    def test_init__activation_must_be_before_expiration(self) -> None:
        now = datetime.datetime.now(tz=datetime.UTC)

        with pytest.raises(pydantic.ValidationError, match="activation timestamp must be earlier than expiration"):
            make_effective_entitlement_interval(starts_at=now, expires_at=now)
