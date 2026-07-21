import datetime
import enum
import uuid
from typing import NewType

from ffun.core.entities import BaseEntity
from ffun.domain.entities import SerializedId

AuditRecordId = NewType("AuditRecordId", uuid.UUID)
AuditEventName = NewType("AuditEventName", str)


class AuditEntityKind(enum.IntEnum):
    user = 1
    admin = 2
    psp = 3
    system = 4


class AuditRecord(BaseEntity):
    id: AuditRecordId
    created_at: datetime.datetime
    event: AuditEventName
    actor_kind: AuditEntityKind
    actor_id: SerializedId
    subject_kind: AuditEntityKind
    subject_id: SerializedId
    attributes: dict[str, object]
