import datetime
import uuid
from typing import cast

import pytest
from psycopg import IntegrityError
from pytest_mock import MockerFixture

from ffun.audit import operations
from ffun.audit.entities import AuditEntityKind, AuditEventName
from ffun.audit.tests.helpers import load_audit_record
from ffun.core.postgresql import execute, transaction
from ffun.core.tests.helpers import TableSizeDelta, TableSizeNotChanged
from ffun.domain.entities import SerializedId


class TestNewAuditRecordId:
    def test_returns_unique_uuid(self) -> None:
        first_id = operations.new_audit_record_id()
        second_id = operations.new_audit_record_id()

        assert isinstance(first_id, uuid.UUID)
        assert isinstance(second_id, uuid.UUID)
        assert first_id != second_id


class TestRecord:
    @pytest.mark.asyncio
    async def test_default_attributes(self) -> None:
        async with TableSizeDelta("a_records", delta=1):
            record_id = await operations.record(
                execute,
                event=AuditEventName("system_started"),
                actor_kind=AuditEntityKind.system,
                actor_id=SerializedId("system"),
                subject_kind=AuditEntityKind.system,
                subject_id=SerializedId("system"),
            )

        record = await load_audit_record(record_id)
        assert record.attributes == {}

    @pytest.mark.asyncio
    async def test_inserts_record(self) -> None:
        before_insert = datetime.datetime.now(tz=datetime.timezone.utc)

        async with TableSizeDelta("a_records", delta=1):
            record_id = await operations.record(
                execute,
                event=AuditEventName("user_changed"),
                actor_kind=AuditEntityKind.admin,
                actor_id=SerializedId("admin-1"),
                subject_kind=AuditEntityKind.user,
                subject_id=SerializedId("user-1"),
                attributes={"enabled": True},
            )

        assert isinstance(record_id, uuid.UUID)

        record = await load_audit_record(record_id)
        assert record.id == record_id
        assert before_insert <= record.created_at <= datetime.datetime.now(tz=datetime.timezone.utc)
        assert record.event == "user_changed"
        assert record.actor_kind == AuditEntityKind.admin
        assert record.actor_id == "admin-1"
        assert record.subject_kind == AuditEntityKind.user
        assert record.subject_id == "user-1"
        assert record.attributes == {"enabled": True}

    @pytest.mark.asyncio
    async def test_duplicate_id_does_not_replace_record(self, mocker: MockerFixture) -> None:
        record_id = operations.new_audit_record_id()
        mocker.patch.object(operations, "new_audit_record_id", return_value=record_id)

        async with TableSizeDelta("a_records", delta=1):
            await operations.record(
                execute,
                event=AuditEventName("original_event"),
                actor_kind=AuditEntityKind.system,
                actor_id=SerializedId("system-1"),
                subject_kind=AuditEntityKind.user,
                subject_id=SerializedId("user-1"),
                attributes={},
            )

        integrity_error = cast(type[Exception], IntegrityError)

        async with TableSizeNotChanged("a_records"):
            with pytest.raises(integrity_error):
                await operations.record(
                    execute,
                    event=AuditEventName("replacement_event"),
                    actor_kind=AuditEntityKind.system,
                    actor_id=SerializedId("system-2"),
                    subject_kind=AuditEntityKind.user,
                    subject_id=SerializedId("user-2"),
                    attributes={"replacement": True},
                )

        record = await load_audit_record(record_id)
        assert record.event == "original_event"
        assert record.actor_id == "system-1"
        assert record.subject_id == "user-1"
        assert record.attributes == {}

    @pytest.mark.asyncio
    async def test_caller_transaction_rollback_removes_record(self) -> None:
        class RollbackTransaction(Exception):
            pass

        record_id = None

        async with TableSizeNotChanged("a_records"):
            with pytest.raises(RollbackTransaction):
                async with transaction() as transaction_execute:
                    record_id = await operations.record(
                        transaction_execute,
                        event=AuditEventName("user_changed"),
                        actor_kind=AuditEntityKind.admin,
                        actor_id=SerializedId("admin-1"),
                        subject_kind=AuditEntityKind.user,
                        subject_id=SerializedId("user-1"),
                    )
                    raise RollbackTransaction()

        assert record_id is not None
        rows = cast(
            list[dict[str, object]],
            await execute("SELECT id FROM a_records WHERE id = %(id)s", {"id": record_id}),  # type: ignore[misc]
        )
        assert rows == []
