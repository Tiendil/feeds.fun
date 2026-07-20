from ffun.audit import domain, operations


class TestNewAuditRecordId:
    def test_reexports_operation(self) -> None:
        assert domain.new_audit_record_id is operations.new_audit_record_id


class TestRecord:
    def test_reexports_operation(self) -> None:
        assert domain.record is operations.record


class TestLoadRecordsForSubject:
    def test_reexports_operation(self) -> None:
        assert domain.load_records_for_subject is operations.load_records_for_subject
