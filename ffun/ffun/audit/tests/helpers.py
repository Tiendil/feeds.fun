from typing import cast

from ffun.audit.entities import AuditRecord, AuditRecordId
from ffun.core.postgresql import execute


async def load_audit_record(record_id: AuditRecordId) -> AuditRecord:
    sql = """
    SELECT *
    FROM a_records
    WHERE id = %(id)s
    """

    rows = cast(
        list[dict[str, object]],
        await execute(sql, {"id": record_id}),  # type: ignore[misc]
    )

    assert len(rows) == 1

    return AuditRecord.model_validate(rows[0])
