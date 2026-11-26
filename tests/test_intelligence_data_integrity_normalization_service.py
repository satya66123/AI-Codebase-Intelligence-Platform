import pytest

from app.application.intelligence_data_integrity_normalization_service import (
    IntegrityFinding,
    IntegritySeverity,
    IntelligenceDataIntegrityError,
    IntelligenceDataIntegrityNormalizationService,
    IntelligenceDataIntegrityReport,
    NormalizedIntelligenceRecord,
)


class TestIntelligenceDataIntegrityNormalizationService:
    def setup_method(self):
        self.service = IntelligenceDataIntegrityNormalizationService(
            required_fields=("id",),
            text_fields=("name", "description"),
            path_fields=("file_path",),
        )

    def test_valid_record_is_normalized(self):
        result = self.service.normalize(
            [
                {
                    "id": "entity-1",
                    "name": "User Service",
                    "description": "Handles user operations",
                    "file_path": "app/services/user.py",
                }
            ]
        )

        assert result.is_valid is True
        assert result.total_records == 1
        assert result.normalized_records == 1
        assert result.invalid_records == 0
        assert result.records[0].data["id"] == "entity-1"

    def test_empty_input_returns_empty_report(self):
        result = self.service.normalize([])

        assert result.total_records == 0
        assert result.normalized_records == 0
        assert result.invalid_records == 0
        assert result.records == ()
        assert result.findings == ()
        assert result.is_valid is True

    def test_text_whitespace_is_collapsed(self):
        result = self.service.normalize(
            [
                {
                    "id": "entity-1",
                    "name": "  User    Management   Service ",
                    "description": "  Handles   user\n operations ",
                }
            ]
        )

        record = result.records[0]

        assert record.data["name"] == "User Management Service"
        assert record.data["description"] == "Handles user operations"
        assert set(record.changed_fields) == {"name", "description"}

    def test_text_normalization_generates_info_findings(self):
        result = self.service.normalize(
            [{"id": "entity-1", "name": "  User Service  "}]
        )

        findings = [
            finding
            for finding in result.findings
            if finding.code == "TEXT_NORMALIZED"
        ]

        assert len(findings) == 1
        assert findings[0].severity is IntegritySeverity.INFO
        assert findings[0].field_name == "name"

    def test_text_with_no_extra_whitespace_is_unchanged(self):
        result = self.service.normalize(
            [{"id": "entity-1", "name": "User Service"}]
        )

        assert result.records[0].data["name"] == "User Service"
        assert result.records[0].changed_fields == ()
        assert result.changed_field_count == 0

    def test_empty_text_is_preserved(self):
        result = self.service.normalize(
            [{"id": "entity-1", "name": ""}]
        )

        assert result.records[0].data["name"] == ""
        assert result.is_valid is True

    def test_non_string_text_field_is_invalid(self):
        result = self.service.normalize(
            [{"id": "entity-1", "name": 123}]
        )

        assert result.invalid_records == 1
        assert result.normalized_records == 0
        assert result.is_valid is False
        assert any(
            finding.code == "INVALID_TEXT_FIELD"
            for finding in result.findings
        )

    def test_none_text_field_is_ignored(self):
        result = self.service.normalize(
            [{"id": "entity-1", "name": None}]
        )

        assert result.is_valid is True
        assert result.normalized_records == 1

    def test_windows_path_is_normalized(self):
        result = self.service.normalize(
            [
                {
                    "id": "entity-1",
                    "file_path": r"app\services\user.py",
                }
            ]
        )

        assert result.records[0].data["file_path"] == "app/services/user.py"

    def test_repeated_path_separators_are_normalized(self):
        result = self.service.normalize(
            [
                {
                    "id": "entity-1",
                    "file_path": "app//services///user.py",
                }
            ]
        )

        assert result.records[0].data["file_path"] == "app/services/user.py"

    def test_dot_path_segments_are_normalized(self):
        result = self.service.normalize(
            [
                {
                    "id": "entity-1",
                    "file_path": "app/./services/user.py",
                }
            ]
        )

        assert result.records[0].data["file_path"] == "app/services/user.py"

    def test_path_with_parent_segment_inside_root_is_normalized(self):
        result = self.service.normalize(
            [
                {
                    "id": "entity-1",
                    "file_path": "app/services/../models/user.py",
                }
            ]
        )

        assert result.records[0].data["file_path"] == "app/models/user.py"

    def test_absolute_unix_path_is_rejected_by_default(self):
        result = self.service.normalize(
            [
                {
                    "id": "entity-1",
                    "file_path": "/home/user/project/main.py",
                }
            ]
        )

        assert result.invalid_records == 1
        assert any(
            finding.code == "ABSOLUTE_PATH_NOT_ALLOWED"
            for finding in result.findings
        )

    def test_absolute_windows_path_is_rejected_by_default(self):
        result = self.service.normalize(
            [
                {
                    "id": "entity-1",
                    "file_path": r"C:\project\main.py",
                }
            ]
        )

        assert result.invalid_records == 1
        assert any(
            finding.code == "ABSOLUTE_PATH_NOT_ALLOWED"
            for finding in result.findings
        )

    def test_path_traversal_is_rejected(self):
        result = self.service.normalize(
            [
                {
                    "id": "entity-1",
                    "file_path": "../../outside/main.py",
                }
            ]
        )

        assert result.invalid_records == 1
        assert any(
            finding.code == "PATH_TRAVERSAL_NOT_ALLOWED"
            for finding in result.findings
        )

    def test_path_traversal_after_normalization_is_rejected(self):
        result = self.service.normalize(
            [
                {
                    "id": "entity-1",
                    "file_path": "app/../../outside/main.py",
                }
            ]
        )

        assert result.invalid_records == 1
        assert any(
            finding.code == "PATH_TRAVERSAL_NOT_ALLOWED"
            for finding in result.findings
        )

    def test_absolute_paths_can_be_allowed_by_configuration(self):
        service = IntelligenceDataIntegrityNormalizationService(
            reject_absolute_paths=False
        )

        result = service.normalize(
            [
                {
                    "id": "entity-1",
                    "file_path": "/home/user/main.py",
                }
            ]
        )

        assert result.is_valid is True
        assert result.records[0].data["file_path"] == "/home/user/main.py"

    def test_empty_path_is_invalid(self):
        result = self.service.normalize(
            [{"id": "entity-1", "file_path": "   "}]
        )

        assert result.invalid_records == 1
        assert any(
            finding.code == "INVALID_PATH_FIELD"
            for finding in result.findings
        )

    def test_non_string_path_is_invalid(self):
        result = self.service.normalize(
            [{"id": "entity-1", "file_path": 123}]
        )

        assert result.invalid_records == 1
        assert any(
            finding.code == "INVALID_PATH_FIELD"
            for finding in result.findings
        )

    def test_missing_required_field_is_reported(self):
        result = self.service.normalize(
            [{"name": "User Service"}]
        )

        assert result.invalid_records == 1
        assert result.normalized_records == 0
        assert any(
            finding.code == "MISSING_REQUIRED_FIELD"
            and finding.field_name == "id"
            for finding in result.findings
        )

    def test_none_required_field_is_reported(self):
        result = self.service.normalize(
            [{"id": None}]
        )

        assert result.invalid_records == 1
        assert any(
            finding.code == "MISSING_REQUIRED_FIELD"
            for finding in result.findings
        )

    def test_empty_identifier_is_invalid(self):
        result = self.service.normalize(
            [{"id": "   "}]
        )

        assert result.invalid_records == 1
        assert any(
            finding.code == "INVALID_IDENTIFIER"
            for finding in result.findings
        )

    def test_non_string_identifier_is_invalid(self):
        result = self.service.normalize(
            [{"id": 123}]
        )

        assert result.invalid_records == 1
        assert any(
            finding.code == "INVALID_IDENTIFIER"
            for finding in result.findings
        )

    def test_identifier_whitespace_is_trimmed(self):
        result = self.service.normalize(
            [{"id": "  entity-1  "}]
        )

        assert result.records[0].data["id"] == "entity-1"
        assert "id" in result.records[0].changed_fields
        assert any(
            finding.code == "IDENTIFIER_NORMALIZED"
            for finding in result.findings
        )

    def test_exact_duplicate_record_is_reported_as_warning(self):
        record = {"id": "entity-1", "name": "User Service"}

        result = self.service.normalize([record, record.copy()])

        assert result.duplicate_records == 1
        assert result.invalid_records == 0
        assert result.normalized_records == 2
        assert result.is_valid is True
        assert any(
            finding.code == "DUPLICATE_RECORD"
            and finding.severity is IntegritySeverity.WARNING
            for finding in result.findings
        )

    def test_conflicting_identifier_is_reported_as_error(self):
        result = self.service.normalize(
            [
                {"id": "entity-1", "name": "User Service"},
                {"id": "entity-1", "name": "Account Service"},
            ]
        )

        assert result.duplicate_records == 1
        assert result.invalid_records == 1
        assert result.normalized_records == 1
        assert result.is_valid is False
        assert any(
            finding.code == "CONFLICTING_IDENTIFIER"
            and finding.severity is IntegritySeverity.ERROR
            for finding in result.findings
        )

    def test_identifier_comparison_is_case_sensitive_by_default(self):
        result = self.service.normalize(
            [
                {"id": "Entity-1"},
                {"id": "entity-1"},
            ]
        )

        assert result.duplicate_records == 0
        assert result.invalid_records == 0

    def test_identifier_comparison_can_be_case_insensitive(self):
        service = IntelligenceDataIntegrityNormalizationService(
            case_insensitive_identifiers=True
        )

        result = service.normalize(
            [
                {"id": "Entity-1"},
                {"id": "entity-1"},
            ]
        )

        assert result.duplicate_records == 1
        assert result.invalid_records == 1
        assert any(
            finding.code == "CONFLICTING_IDENTIFIER"
            for finding in result.findings
        )

    def test_invalid_record_type_is_reported(self):
        result = self.service.normalize(
            [{"id": "entity-1"}, "invalid-record"]
        )

        assert result.total_records == 2
        assert result.normalized_records == 1
        assert result.invalid_records == 1
        assert any(
            finding.code == "INVALID_RECORD_TYPE"
            for finding in result.findings
        )

    def test_invalid_record_does_not_prevent_later_records(self):
        result = self.service.normalize(
            [
                {"name": "Missing ID"},
                {"id": "entity-2", "name": "Valid Entity"},
            ]
        )

        assert result.total_records == 2
        assert result.invalid_records == 1
        assert result.normalized_records == 1
        assert result.records[0].data["id"] == "entity-2"

    def test_original_input_records_are_not_mutated(self):
        original = {
            "id": "entity-1",
            "name": "  User   Service  ",
            "file_path": r"app\services\user.py",
        }

        self.service.normalize([original])

        assert original["name"] == "  User   Service  "
        assert original["file_path"] == r"app\services\user.py"

    def test_unconfigured_fields_are_preserved(self):
        result = self.service.normalize(
            [
                {
                    "id": "entity-1",
                    "metadata": {"language": "python"},
                    "count": 5,
                }
            ]
        )

        assert result.records[0].data["metadata"] == {
            "language": "python"
        }
        assert result.records[0].data["count"] == 5

    def test_multiple_changed_fields_are_counted_once_each(self):
        result = self.service.normalize(
            [
                {
                    "id": " entity-1 ",
                    "name": "  User   Service ",
                    "file_path": r"app\services\user.py",
                }
            ]
        )

        assert result.changed_field_count == 3
        assert set(result.records[0].changed_fields) == {
            "id",
            "name",
            "file_path",
        }

    def test_report_counts_findings_by_severity(self):
        result = self.service.normalize(
            [
                {"id": " entity-1 ", "name": "  User Service  "},
                {"id": "entity-1", "name": "Different Service"},
            ]
        )

        assert result.error_count == 1
        assert result.info_count >= 1
        assert result.warning_count == 0

    def test_report_has_warnings_for_exact_duplicate(self):
        record = {"id": "entity-1"}

        result = self.service.normalize([record, record.copy()])

        assert result.has_warnings is True
        assert result.warning_count == 1

    def test_report_is_valid_when_only_info_findings_exist(self):
        result = self.service.normalize(
            [{"id": " entity-1 ", "name": "  User Service  "}]
        )

        assert result.is_valid is True
        assert result.error_count == 0
        assert result.info_count > 0

    def test_report_is_invalid_when_error_findings_exist(self):
        result = self.service.normalize([{"name": "Missing ID"}])

        assert result.is_valid is False
        assert result.error_count > 0

    def test_custom_required_fields_are_supported(self):
        service = IntelligenceDataIntegrityNormalizationService(
            required_fields=("id", "repository_id")
        )

        result = service.normalize(
            [{"id": "entity-1", "repository_id": "repo-1"}]
        )

        assert result.is_valid is True

    def test_custom_identifier_field_is_supported(self):
        service = IntelligenceDataIntegrityNormalizationService(
            required_fields=("entity_id",),
            identifier_field="entity_id",
        )

        result = service.normalize(
            [{"entity_id": "entity-1"}]
        )

        assert result.is_valid is True
        assert result.records[0].data["entity_id"] == "entity-1"

    def test_custom_text_fields_are_supported(self):
        service = IntelligenceDataIntegrityNormalizationService(
            text_fields=("qualified_name",)
        )

        result = service.normalize(
            [{"id": "entity-1", "qualified_name": "  app . services . User  "}]
        )

        assert result.records[0].data["qualified_name"] == (
            "app . services . User"
        )

    def test_custom_path_fields_are_supported(self):
        service = IntelligenceDataIntegrityNormalizationService(
            path_fields=("source_file",)
        )

        result = service.normalize(
            [{"id": "entity-1", "source_file": r"app\models\user.py"}]
        )

        assert result.records[0].data["source_file"] == "app/models/user.py"

    def test_required_fields_must_be_iterable(self):
        with pytest.raises(IntelligenceDataIntegrityError):
            IntelligenceDataIntegrityNormalizationService(
                required_fields="id"
            )

    def test_text_fields_must_be_iterable(self):
        with pytest.raises(IntelligenceDataIntegrityError):
            IntelligenceDataIntegrityNormalizationService(
                text_fields="name"
            )

    def test_path_fields_must_be_iterable(self):
        with pytest.raises(IntelligenceDataIntegrityError):
            IntelligenceDataIntegrityNormalizationService(
                path_fields="file_path"
            )

    def test_field_collection_rejects_empty_field_names(self):
        with pytest.raises(IntelligenceDataIntegrityError):
            IntelligenceDataIntegrityNormalizationService(
                text_fields=("name", " ")
            )

    def test_field_collection_rejects_duplicate_names(self):
        with pytest.raises(IntelligenceDataIntegrityError):
            IntelligenceDataIntegrityNormalizationService(
                text_fields=("name", "name")
            )

    def test_identifier_field_must_be_non_empty(self):
        with pytest.raises(IntelligenceDataIntegrityError):
            IntelligenceDataIntegrityNormalizationService(
                identifier_field=" "
            )

    def test_case_insensitive_option_must_be_boolean(self):
        with pytest.raises(IntelligenceDataIntegrityError):
            IntelligenceDataIntegrityNormalizationService(
                case_insensitive_identifiers=1
            )

    def test_reject_absolute_paths_option_must_be_boolean(self):
        with pytest.raises(IntelligenceDataIntegrityError):
            IntelligenceDataIntegrityNormalizationService(
                reject_absolute_paths=1
            )

    def test_string_input_is_rejected(self):
        with pytest.raises(IntelligenceDataIntegrityError):
            self.service.normalize("invalid")

    def test_mapping_input_is_rejected(self):
        with pytest.raises(IntelligenceDataIntegrityError):
            self.service.normalize({"id": "entity-1"})

    def test_non_iterable_input_is_rejected(self):
        with pytest.raises(IntelligenceDataIntegrityError):
            self.service.normalize(123)

    def test_finding_model_rejects_empty_code(self):
        with pytest.raises(IntelligenceDataIntegrityError):
            IntegrityFinding(
                code=" ",
                severity=IntegritySeverity.ERROR,
                record_index=0,
                field_name="id",
                message="Missing identifier.",
            )

    def test_finding_model_rejects_invalid_severity(self):
        with pytest.raises(IntelligenceDataIntegrityError):
            IntegrityFinding(
                code="INVALID",
                severity="error",
                record_index=0,
                field_name="id",
                message="Missing identifier.",
            )

    def test_finding_model_rejects_negative_record_index(self):
        with pytest.raises(IntelligenceDataIntegrityError):
            IntegrityFinding(
                code="INVALID",
                severity=IntegritySeverity.ERROR,
                record_index=-1,
                field_name="id",
                message="Invalid record.",
            )

    def test_normalized_record_rejects_invalid_data(self):
        with pytest.raises(IntelligenceDataIntegrityError):
            NormalizedIntelligenceRecord(
                record_index=0,
                data="invalid",
                changed_fields=(),
            )

    def test_normalized_record_rejects_invalid_changed_fields(self):
        with pytest.raises(IntelligenceDataIntegrityError):
            NormalizedIntelligenceRecord(
                record_index=0,
                data={"id": "entity-1"},
                changed_fields=("name", 123),
            )

    def test_report_rejects_negative_counts(self):
        with pytest.raises(IntelligenceDataIntegrityError):
            IntelligenceDataIntegrityReport(
                total_records=-1,
                normalized_records=0,
                invalid_records=0,
                duplicate_records=0,
                changed_field_count=0,
                records=(),
                findings=(),
            )

    def test_report_rejects_inconsistent_record_counts(self):
        with pytest.raises(IntelligenceDataIntegrityError):
            IntelligenceDataIntegrityReport(
                total_records=2,
                normalized_records=1,
                invalid_records=0,
                duplicate_records=0,
                changed_field_count=0,
                records=(),
                findings=(),
            )

    def test_report_rejects_invalid_records_collection(self):
        with pytest.raises(IntelligenceDataIntegrityError):
            IntelligenceDataIntegrityReport(
                total_records=0,
                normalized_records=0,
                invalid_records=0,
                duplicate_records=0,
                changed_field_count=0,
                records=[],
                findings=(),
            )

    def test_report_rejects_invalid_findings_collection(self):
        with pytest.raises(IntelligenceDataIntegrityError):
            IntelligenceDataIntegrityReport(
                total_records=0,
                normalized_records=0,
                invalid_records=0,
                duplicate_records=0,
                changed_field_count=0,
                records=(),
                findings=[],
            )