import datetime
from typing import cast

import pydantic
import pytest

from ffun.entitlements.entities import ENTITLEMENT_KINDS, EntitlementKindId, MergePolicy
from ffun.entitlements.tests.make import make_source_entitlement


class TestEntitlementKindId:
    def test_members_are_closed_and_stable(self) -> None:
        assert list(EntitlementKindId) == [
            EntitlementKindId.day_tokens,
            EntitlementKindId.month_tokens,
        ]
        assert [kind_id.value for kind_id in EntitlementKindId] == [1, 2]

        with pytest.raises(ValueError):
            EntitlementKindId(999)


class TestEntitlementKinds:
    def test_registry_defines_every_kind_once(self) -> None:
        assert [kind.id for kind in ENTITLEMENT_KINDS] == list(EntitlementKindId)
        assert [kind.merge_policy for kind in ENTITLEMENT_KINDS] == [MergePolicy.max, MergePolicy.max]


class TestSourceEntitlement:
    def test_init__granted_requires_boolean(self) -> None:
        with pytest.raises(pydantic.ValidationError, match="valid boolean"):
            make_source_entitlement(granted=cast(bool, 1))

    @pytest.mark.parametrize("value", [None, True])
    def test_init__grant_requires_integer_value(self, value: object) -> None:
        with pytest.raises(pydantic.ValidationError, match="integer"):
            make_source_entitlement(value=cast(int | None, value))

    def test_init__revocation_requires_no_value(self) -> None:
        with pytest.raises(pydantic.ValidationError, match="must not have a value"):
            make_source_entitlement(granted=False, value=10)

    def test_init__activation_requires_utc_offset(self) -> None:
        now = datetime.datetime.now(tz=datetime.UTC)

        with pytest.raises(pydantic.ValidationError, match="activation timestamp must have a UTC offset"):
            make_source_entitlement(starts_at=now.replace(tzinfo=None))

    def test_init__expiration_requires_utc_offset(self) -> None:
        now = datetime.datetime.now(tz=datetime.UTC)

        with pytest.raises(pydantic.ValidationError, match="expiration timestamp must have a UTC offset"):
            make_source_entitlement(expires_at=now.replace(tzinfo=None))

    def test_init__activation_must_be_before_expiration(self) -> None:
        now = datetime.datetime.now(tz=datetime.UTC)

        with pytest.raises(pydantic.ValidationError, match="activation timestamp must be earlier than expiration"):
            make_source_entitlement(starts_at=now, expires_at=now)

    def test_to_revoked__returns_revocation_for_new_interval(self) -> None:
        entitlement = make_source_entitlement()
        starts_at = entitlement.expires_at
        expires_at = starts_at + datetime.timedelta(days=1)

        revoked = entitlement.to_revoked(starts_at=starts_at, expires_at=expires_at)

        assert revoked == make_source_entitlement(
            source=entitlement.source,
            user_id=entitlement.user_id,
            kind_id=entitlement.kind_id,
            granted=False,
            value=None,
            starts_at=starts_at,
            expires_at=expires_at,
        )

    def test_to_granted__returns_grant_for_new_interval(self) -> None:
        entitlement = make_source_entitlement(granted=False, value=None)
        starts_at = entitlement.expires_at
        expires_at = starts_at + datetime.timedelta(days=1)

        granted = entitlement.to_granted(value=20, starts_at=starts_at, expires_at=expires_at)

        assert granted == make_source_entitlement(
            source=entitlement.source,
            user_id=entitlement.user_id,
            kind_id=entitlement.kind_id,
            granted=True,
            value=20,
            starts_at=starts_at,
            expires_at=expires_at,
        )
