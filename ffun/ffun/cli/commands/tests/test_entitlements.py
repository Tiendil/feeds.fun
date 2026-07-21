import datetime

import pytest
import typer

from ffun.audit.entities import AuditEntityKind
from ffun.cli.commands import entitlements
from ffun.domain.domain import new_user_id
from ffun.entitlements.entities import EntitlementKindId
from ffun.entitlements.tests.make import make_effective_entitlement_interval


class TestEntitlementKindFromName:
    @pytest.mark.parametrize("kind", list(EntitlementKindId))
    def test_registered_name(self, kind: EntitlementKindId) -> None:
        assert entitlements.entitlement_kind_from_name(kind.name) == kind

    def test_rejects_numeric_value(self) -> None:
        with pytest.raises(typer.BadParameter):
            entitlements.entitlement_kind_from_name(str(EntitlementKindId.day_tokens.value))

    def test_rejects_unknown_name(self) -> None:
        with pytest.raises(typer.BadParameter):
            entitlements.entitlement_kind_from_name("unknown")


class TestActorKindFromName:
    @pytest.mark.parametrize("kind", list(AuditEntityKind))
    def test_registered_name(self, kind: AuditEntityKind) -> None:
        assert entitlements.actor_kind_from_name(kind.name) == kind

    def test_rejects_unknown_name(self) -> None:
        with pytest.raises(typer.BadParameter):
            entitlements.actor_kind_from_name("unknown")


class TestTimestampFromString:
    def test_missing_value(self) -> None:
        assert entitlements.timestamp_from_string(None, option_name="--starts-at") is None

    def test_iso_8601_with_utc_offset(self) -> None:
        timestamp = datetime.datetime.now(tz=datetime.timezone(datetime.timedelta(hours=2)))

        assert entitlements.timestamp_from_string(timestamp.isoformat(), option_name="--starts-at") == timestamp

    def test_rejects_invalid_value(self) -> None:
        with pytest.raises(typer.BadParameter):
            entitlements.timestamp_from_string("not-a-timestamp", option_name="--starts-at")

    def test_rejects_value_without_utc_offset(self) -> None:
        timestamp = datetime.datetime.now().replace(tzinfo=None)

        with pytest.raises(typer.BadParameter):
            entitlements.timestamp_from_string(timestamp.isoformat(), option_name="--starts-at")


class TestResolveTimestamps:
    def test_defaults_from_one_captured_timestamp(self) -> None:
        captured_at = datetime.datetime.now(tz=datetime.UTC)

        starts_at, expires_at = entitlements.resolve_timestamps(None, None, captured_at)

        assert starts_at == captured_at
        assert expires_at == captured_at + datetime.timedelta(days=31)

    def test_preserves_explicit_values(self) -> None:
        starts_at = datetime.datetime.now(tz=datetime.UTC)
        expires_at = starts_at + datetime.timedelta(days=7)

        assert entitlements.resolve_timestamps(starts_at, expires_at, starts_at) == (starts_at, expires_at)

    def test_defaults_only_start(self) -> None:
        captured_at = datetime.datetime.now(tz=datetime.UTC)
        expires_at = captured_at + datetime.timedelta(days=7)

        assert entitlements.resolve_timestamps(None, expires_at, captured_at) == (captured_at, expires_at)

    def test_defaults_only_expiration(self) -> None:
        captured_at = datetime.datetime.now(tz=datetime.UTC)
        starts_at = captured_at - datetime.timedelta(days=1)

        assert entitlements.resolve_timestamps(starts_at, None, captured_at) == (
            starts_at,
            captured_at + datetime.timedelta(days=31),
        )


class TestEntitlementRecord:
    def test_granted(self) -> None:
        user_id = new_user_id()
        interval = make_effective_entitlement_interval(user_id=user_id, kind_id=EntitlementKindId.day_tokens)

        assert entitlements.entitlement_record(user_id, EntitlementKindId.day_tokens, interval) == {
            "user_id": str(user_id),
            "kind": "day_tokens",
            "kind_id": 1,
            "granted": True,
            "value": interval.value,
            "starts_at": interval.starts_at.isoformat(),
            "expires_at": interval.expires_at.isoformat(),
        }

    def test_not_granted(self) -> None:
        user_id = new_user_id()

        assert entitlements.entitlement_record(user_id, EntitlementKindId.month_tokens, None) == {
            "user_id": str(user_id),
            "kind": "month_tokens",
            "kind_id": 2,
            "granted": False,
            "value": None,
            "starts_at": None,
            "expires_at": None,
        }
