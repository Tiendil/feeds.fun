import types
import uuid
from collections.abc import Mapping

from psycopg.types.json import Jsonb

from ffun.audit.entities import AuditEntityKind, AuditEventName, AuditRecordId
from ffun.core.postgresql import ExecuteType
from ffun.domain.entities import SerializedId

_EMPTY_ATTRIBUTES: Mapping[str, object] = types.MappingProxyType({})


def new_audit_record_id() -> AuditRecordId:
    return AuditRecordId(uuid.uuid4())


async def record(  # noqa: CFQ002
    execute: ExecuteType,
    *,
    event: AuditEventName,
    actor_kind: AuditEntityKind,
    actor_id: SerializedId,
    subject_kind: AuditEntityKind,
    subject_id: SerializedId,
    attributes: Mapping[str, object] = _EMPTY_ATTRIBUTES,
) -> AuditRecordId:
    record_id = new_audit_record_id()

    sql = """
    INSERT INTO a_records (
        id,
        event,
        actor_kind,
        actor_id,
        subject_kind,
        subject_id,
        attributes
    )
    VALUES (
        %(id)s,
        %(event)s,
        %(actor_kind)s,
        %(actor_id)s,
        %(subject_kind)s,
        %(subject_id)s,
        %(attributes)s
    )
    """

    await execute(
        sql,
        {
            "id": record_id,
            "event": event,
            "actor_kind": int(actor_kind),
            "actor_id": actor_id,
            "subject_kind": int(subject_kind),
            "subject_id": subject_id,
            "attributes": Jsonb(dict(attributes)),
        },
    )

    return record_id
