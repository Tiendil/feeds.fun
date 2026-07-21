from ffun.audit.entities import AuditEntityKind


class TestAuditEntityKind:
    def test_stable_values(self) -> None:
        assert AuditEntityKind.user.value == 1
        assert AuditEntityKind.admin.value == 2
        assert AuditEntityKind.psp.value == 3
        assert AuditEntityKind.system.value == 4
