from dataclasses import dataclass

import pytest

from app.application.intelligence_result_consistency_validation_service import (
    ConsistencyIssue,
    ConsistencySeverity,
    IntelligenceResultConsistencyError,
    IntelligenceResultConsistencyReport,
    IntelligenceResultConsistencyValidationService,
)


@dataclass
class SampleRecord:
    id: str
    references: tuple[str, ...] = ()


class TestIntelligenceResultConsistencyValidationService:
    def setup_method(self):
        self.service = IntelligenceResultConsistencyValidationService()

    def test_valid_artifacts_produce_consistent_report(self):
        artifacts = {
            "entities": [
                {"id": "entity-1"},
                {"id": "entity-2"},
            ],
            "relationships": [
                {"id": "relationship-1", "references": ["entity-1", "entity-2"]}
            ],
        }

        result = self.service.validate(artifacts)

        assert result.is_consistent is True
        assert result.artifacts_checked == 2
        assert result.records_checked == 3
        assert result.issue_count == 0
        assert result.error_count == 0
        assert result.warning_count == 0
        assert result.info_count == 0

    def test_empty_artifacts_mapping_returns_valid_report(self):
        result = self.service.validate({})

        assert result.is_consistent is True
        assert result.artifacts_checked == 0
        assert result.records_checked == 0
        assert result.issues == ()

    def test_required_artifact_missing_is_error(self):
        service = IntelligenceResultConsistencyValidationService(
            required_artifacts=("entities", "dependencies")
        )

        result = service.validate({"entities": [{"id": "entity-1"}]})

        assert result.is_consistent is False
        assert result.error_count == 1
        assert result.issues[0].code == "MISSING_REQUIRED_ARTIFACT"
        assert result.issues[0].artifact_name == "dependencies"

    def test_multiple_required_artifacts_can_be_missing(self):
        service = IntelligenceResultConsistencyValidationService(
            required_artifacts=("entities", "dependencies", "architecture")
        )

        result = service.validate({})

        assert result.error_count == 3
        assert {
            issue.artifact_name for issue in result.issues
        } == {"entities", "dependencies", "architecture"}

    def test_empty_artifact_is_allowed_by_default(self):
        result = self.service.validate({"entities": []})

        assert result.is_consistent is True
        assert result.artifacts_checked == 1
        assert result.records_checked == 0

    def test_empty_artifact_can_be_rejected(self):
        service = IntelligenceResultConsistencyValidationService(
            allow_empty_artifacts=False
        )

        result = service.validate({"entities": []})

        assert result.is_consistent is False
        assert result.error_count == 1
        assert result.issues[0].code == "EMPTY_ARTIFACT"

    def test_missing_identifier_is_reported(self):
        result = self.service.validate(
            {"entities": [{"name": "User"}, {"id": "entity-2"}]}
        )

        assert result.is_consistent is False
        assert result.error_count == 1
        assert result.issues[0].code == "MISSING_OR_INVALID_IDENTIFIER"
        assert result.issues[0].record_index == 0
        assert result.issues[0].field_name == "id"

    @pytest.mark.parametrize("identifier", [None, "", "   ", 123, [], {}])
    def test_invalid_identifier_is_reported(self, identifier):
        result = self.service.validate(
            {"entities": [{"id": identifier}]}
        )

        assert result.is_consistent is False
        assert result.error_count == 1
        assert result.issues[0].code == "MISSING_OR_INVALID_IDENTIFIER"

    def test_duplicate_identifier_within_same_artifact_is_reported(self):
        result = self.service.validate(
            {
                "entities": [
                    {"id": "entity-1"},
                    {"id": "entity-1"},
                ]
            }
        )

        assert result.is_consistent is False
        assert result.error_count == 1
        assert result.issues[0].code == "DUPLICATE_IDENTIFIER"
        assert result.issues[0].record_index == 1

    def test_duplicate_identifier_across_artifacts_is_reported(self):
        result = self.service.validate(
            {
                "entities": [{"id": "item-1"}],
                "dependencies": [{"id": "item-1"}],
            }
        )

        assert result.is_consistent is False
        assert result.error_count == 1
        assert result.issues[0].code == "DUPLICATE_IDENTIFIER"
        assert result.issues[0].artifact_name == "dependencies"

    def test_unresolved_reference_is_reported(self):
        result = self.service.validate(
            {
                "entities": [{"id": "entity-1"}],
                "relationships": [
                    {"id": "relationship-1", "references": ["missing-entity"]}
                ],
            }
        )

        assert result.is_consistent is False
        assert result.error_count == 1
        assert result.issues[0].code == "UNRESOLVED_REFERENCE"
        assert result.issues[0].field_name == "references"

    def test_reference_to_identifier_in_another_artifact_is_valid(self):
        result = self.service.validate(
            {
                "entities": [{"id": "entity-1"}],
                "relationships": [
                    {"id": "relationship-1", "references": ["entity-1"]}
                ],
            }
        )

        assert result.is_consistent is True
        assert result.issue_count == 0

    def test_string_reference_is_supported(self):
        result = self.service.validate(
            {
                "entities": [{"id": "entity-1"}],
                "relationships": [
                    {"id": "relationship-1", "references": "entity-1"}
                ],
            }
        )

        assert result.is_consistent is True
        assert result.issue_count == 0

    def test_duplicate_references_generate_warning(self):
        result = self.service.validate(
            {
                "entities": [{"id": "entity-1"}],
                "relationships": [
                    {
                        "id": "relationship-1",
                        "references": ["entity-1", "entity-1"],
                    }
                ],
            }
        )

        assert result.is_consistent is True
        assert result.warning_count == 1
        assert result.issues[0].code == "DUPLICATE_REFERENCE"
        assert result.issues[0].severity is ConsistencySeverity.WARNING

    def test_invalid_reference_collection_is_reported(self):
        result = self.service.validate(
            {
                "entities": [{"id": "entity-1"}],
                "relationships": [
                    {"id": "relationship-1", "references": 123}
                ],
            }
        )

        assert result.is_consistent is False
        assert result.error_count == 1
        assert result.issues[0].code == "INVALID_REFERENCE_COLLECTION"

    @pytest.mark.parametrize("reference", [None, "", "   ", 123, {}])
    def test_invalid_reference_value_is_reported(self, reference):
        result = self.service.validate(
            {
                "entities": [{"id": "entity-1"}],
                "relationships": [
                    {"id": "relationship-1", "references": [reference]}
                ],
            }
        )

        assert result.is_consistent is False
        assert result.error_count == 1
        assert result.issues[0].code == "INVALID_REFERENCE"

    def test_related_ids_field_is_validated(self):
        result = self.service.validate(
            {
                "entities": [{"id": "entity-1"}],
                "relationships": [
                    {"id": "relationship-1", "related_ids": ["entity-1"]}
                ],
            }
        )

        assert result.is_consistent is True
        assert result.issue_count == 0

    def test_custom_identifier_field_is_supported(self):
        service = IntelligenceResultConsistencyValidationService(
            identifier_field="entity_id"
        )

        result = service.validate(
            {"entities": [{"entity_id": "entity-1"}]}
        )

        assert result.is_consistent is True
        assert result.issue_count == 0

    def test_custom_reference_fields_are_supported(self):
        service = IntelligenceResultConsistencyValidationService(
            reference_fields=("source_ids",)
        )

        result = service.validate(
            {
                "entities": [{"id": "entity-1"}],
                "relationships": [
                    {"id": "relationship-1", "source_ids": ["entity-1"]}
                ],
            }
        )

        assert result.is_consistent is True
        assert result.issue_count == 0

    def test_custom_missing_reference_severity_can_be_warning(self):
        service = IntelligenceResultConsistencyValidationService(
            missing_reference_severity=ConsistencySeverity.WARNING
        )

        result = service.validate(
            {
                "entities": [{"id": "entity-1"}],
                "relationships": [
                    {"id": "relationship-1", "references": ["missing"]}
                ],
            }
        )

        assert result.is_consistent is True
        assert result.warning_count == 1
        assert result.error_count == 0

    def test_dataclass_records_are_supported(self):
        result = self.service.validate(
            {
                "entities": [
                    SampleRecord(id="entity-1"),
                    SampleRecord(id="entity-2"),
                ],
                "relationships": [
                    SampleRecord(
                        id="relationship-1",
                        references=("entity-1", "entity-2"),
                    )
                ],
            }
        )

        assert result.is_consistent is True
        assert result.records_checked == 3
        assert result.issue_count == 0

    def test_object_records_are_supported(self):
        class Record:
            def __init__(self, record_id):
                self.id = record_id

        result = self.service.validate(
            {"entities": [Record("entity-1")]}
        )

        assert result.is_consistent is True
        assert result.records_checked == 1

    def test_invalid_record_type_is_reported(self):
        result = self.service.validate(
            {"entities": ["not-a-record"]}
        )

        assert result.is_consistent is False
        assert result.error_count == 1
        assert result.issues[0].code == "INVALID_RECORD"

    def test_record_without_reference_fields_is_valid(self):
        result = self.service.validate(
            {"entities": [{"id": "entity-1"}]}
        )

        assert result.is_consistent is True
        assert result.issue_count == 0

    def test_whitespace_around_identifiers_is_normalized(self):
        result = self.service.validate(
            {
                "entities": [{"id": " entity-1 "}],
                "relationships": [
                    {"id": "relationship-1", "references": [" entity-1 "]}
                ],
            }
        )

        assert result.is_consistent is True
        assert result.issue_count == 0

    def test_duplicate_identifiers_are_detected_after_normalization(self):
        result = self.service.validate(
            {
                "entities": [
                    {"id": "entity-1"},
                    {"id": " entity-1 "},
                ]
            }
        )

        assert result.is_consistent is False
        assert result.issues[0].code == "DUPLICATE_IDENTIFIER"

    def test_report_counts_match_issues(self):
        result = self.service.validate(
            {
                "entities": [
                    {"id": "entity-1"},
                    {"id": "entity-1"},
                ],
                "relationships": [
                    {
                        "id": "relationship-1",
                        "references": ["entity-1", "entity-1", "missing"],
                    }
                ],
            }
        )

        assert result.issue_count == 3
        assert result.error_count == 2
        assert result.warning_count == 1
        assert result.info_count == 0
        assert result.has_errors is True
        assert result.has_warnings is True

    def test_issues_by_severity_returns_matching_issues(self):
        result = self.service.validate(
            {
                "entities": [{"id": "entity-1"}],
                "relationships": [
                    {
                        "id": "relationship-1",
                        "references": ["entity-1", "entity-1", "missing"],
                    }
                ],
            }
        )

        errors = result.issues_by_severity(ConsistencySeverity.ERROR)
        warnings = result.issues_by_severity(ConsistencySeverity.WARNING)

        assert len(errors) == 1
        assert len(warnings) == 1
        assert errors[0].code == "UNRESOLVED_REFERENCE"
        assert warnings[0].code == "DUPLICATE_REFERENCE"

    def test_issues_by_severity_rejects_invalid_severity(self):
        result = self.service.validate({})

        with pytest.raises(IntelligenceResultConsistencyError):
            result.issues_by_severity("error")

    def test_non_mapping_artifacts_input_is_rejected(self):
        with pytest.raises(IntelligenceResultConsistencyError):
            self.service.validate([])

    @pytest.mark.parametrize("records", ["text", b"bytes", {"id": "entity-1"}])
    def test_invalid_artifact_collection_is_rejected(self, records):
        with pytest.raises(IntelligenceResultConsistencyError):
            self.service.validate({"entities": records})

    def test_non_iterable_artifact_is_rejected(self):
        with pytest.raises(IntelligenceResultConsistencyError):
            self.service.validate({"entities": 123})

    def test_empty_artifact_name_is_rejected(self):
        with pytest.raises(IntelligenceResultConsistencyError):
            self.service.validate({" ": [{"id": "entity-1"}]})

    def test_required_artifacts_must_be_iterable(self):
        with pytest.raises(IntelligenceResultConsistencyError):
            IntelligenceResultConsistencyValidationService(
                required_artifacts="entities"
            )

    def test_required_artifacts_cannot_contain_duplicates(self):
        with pytest.raises(IntelligenceResultConsistencyError):
            IntelligenceResultConsistencyValidationService(
                required_artifacts=("entities", "entities")
            )

    def test_reference_fields_must_be_iterable(self):
        with pytest.raises(IntelligenceResultConsistencyError):
            IntelligenceResultConsistencyValidationService(
                reference_fields="references"
            )

    def test_identifier_field_must_be_non_empty(self):
        with pytest.raises(IntelligenceResultConsistencyError):
            IntelligenceResultConsistencyValidationService(
                identifier_field=" "
            )

    def test_allow_empty_artifacts_must_be_boolean(self):
        with pytest.raises(IntelligenceResultConsistencyError):
            IntelligenceResultConsistencyValidationService(
                allow_empty_artifacts=1
            )

    def test_missing_reference_severity_must_be_enum(self):
        with pytest.raises(IntelligenceResultConsistencyError):
            IntelligenceResultConsistencyValidationService(
                missing_reference_severity="error"
            )

    def test_issue_model_rejects_empty_code(self):
        with pytest.raises(IntelligenceResultConsistencyError):
            ConsistencyIssue(
                code=" ",
                severity=ConsistencySeverity.ERROR,
                artifact_name="entities",
                message="Invalid identifier.",
            )

    def test_issue_model_rejects_invalid_severity(self):
        with pytest.raises(IntelligenceResultConsistencyError):
            ConsistencyIssue(
                code="INVALID",
                severity="error",
                artifact_name="entities",
                message="Invalid identifier.",
            )

    def test_issue_model_rejects_invalid_record_index(self):
        with pytest.raises(IntelligenceResultConsistencyError):
            ConsistencyIssue(
                code="INVALID",
                severity=ConsistencySeverity.ERROR,
                artifact_name="entities",
                message="Invalid identifier.",
                record_index=-1,
            )

    def test_report_rejects_negative_counts(self):
        with pytest.raises(IntelligenceResultConsistencyError):
            IntelligenceResultConsistencyReport(
                artifacts_checked=-1,
                records_checked=0,
                issues=(),
                is_consistent=True,
                error_count=0,
                warning_count=0,
                info_count=0,
            )

    def test_report_rejects_inconsistent_issue_counts(self):
        with pytest.raises(IntelligenceResultConsistencyError):
            IntelligenceResultConsistencyReport(
                artifacts_checked=1,
                records_checked=1,
                issues=(
                    ConsistencyIssue(
                        code="INVALID",
                        severity=ConsistencySeverity.ERROR,
                        artifact_name="entities",
                        message="Invalid record.",
                    ),
                ),
                is_consistent=False,
                error_count=0,
                warning_count=0,
                info_count=0,
            )

    def test_report_rejects_consistent_flag_when_errors_exist(self):
        with pytest.raises(IntelligenceResultConsistencyError):
            IntelligenceResultConsistencyReport(
                artifacts_checked=1,
                records_checked=1,
                issues=(
                    ConsistencyIssue(
                        code="INVALID",
                        severity=ConsistencySeverity.ERROR,
                        artifact_name="entities",
                        message="Invalid record.",
                    ),
                ),
                is_consistent=True,
                error_count=1,
                warning_count=0,
                info_count=0,
            )