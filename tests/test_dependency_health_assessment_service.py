
"""Tests for DependencyHealthAssessmentService."""

from dataclasses import FrozenInstanceError

import pytest

from appy.application.circular_dependency_detection_service import (
    CircularDependencyDetectionResult,
)
from appy.application.dependency_consistency_validation_service import (
    DependencyConsistencyIssue,
    DependencyConsistencySeverity,
    DependencyConsistencyValidationResult,
)
from appy.application.dependency_health_assessment_service import (
    DependencyHealthAssessment,
    DependencyHealthAssessmentError,
    DependencyHealthAssessmentService,
    DependencyHealthFinding,
    DependencyHealthSeverity,
    DependencyHealthStatus,
)
from appy.application.import_reference_validation_service import (
    ImportReferenceIssue,
    ImportReferenceRecord,
    ImportReferenceSeverity,
    ImportReferenceStatus,
    ImportReferenceValidationResult,
)


@pytest.fixture
def service():
    return DependencyHealthAssessmentService()


def consistency_result(
    *,
    imports_checked=0,
    errors=0,
    warnings=0,
):
    issues = []

    for index in range(errors):
        issues.append(
            DependencyConsistencyIssue(
                code=f"CONSISTENCY_ERROR_{index}",
                message="Dependency consistency error.",
                source_file="appy/example.py",
                line=index + 1,
                severity=DependencyConsistencySeverity.ERROR,
            )
        )

    for index in range(warnings):
        issues.append(
            DependencyConsistencyIssue(
                code=f"CONSISTENCY_WARNING_{index}",
                message="Dependency consistency warning.",
                source_file="appy/example.py",
                line=errors + index + 1,
                severity=DependencyConsistencySeverity.WARNING,
            )
        )

    return DependencyConsistencyValidationResult(
        is_valid=not issues,
        imports_checked=imports_checked,
        dependencies_checked=imports_checked,
        matched_dependencies=max(0, imports_checked - errors),
        missing_dependencies=0,
        unexpected_dependencies=0,
        mismatched_classifications=0,
        issues=tuple(issues),
    )


def import_result(
    *,
    valid=0,
    invalid=0,
    unresolved=0,
    external=0,
):
    records = []
    issues = []

    entries = (
        (valid, ImportReferenceStatus.VALID),
        (invalid, ImportReferenceStatus.INVALID),
        (unresolved, ImportReferenceStatus.UNRESOLVED),
        (external, ImportReferenceStatus.EXTERNAL),
    )

    for count, status in entries:
        for _ in range(count):
            records.append(
                ImportReferenceRecord(
                    source_file="appy/example.py",
                    line=len(records) + 1,
                    imported_module="appy.example",
                    imported_name=None,
                    alias=None,
                    status=status,
                    message=f"Reference status: {status.value}",
                )
            )
            if status != ImportReferenceStatus.VALID:
                severity = (
                    ImportReferenceSeverity.ERROR
                    if status == ImportReferenceStatus.INVALID
                    else ImportReferenceSeverity.WARNING
                )
                issues.append(
                    ImportReferenceIssue(
                        code=f"IMPORT_{status.value.upper()}",
                        message=f"Import reference is {status.value}.",
                        source_file="appy/example.py",
                        line=len(records),
                        severity=severity,
                        status=status,
                        imported_module="appy.example",
                        imported_name=None,
                    )
                )

    return ImportReferenceValidationResult(
        total_imports=valid + invalid + unresolved + external,
        valid_imports=valid,
        invalid_imports=invalid,
        unresolved_imports=unresolved,
        external_imports=external,
        records=tuple(records),
        issues=tuple(issues),
    )


def circular_result(cycle_count=0):
    return CircularDependencyDetectionResult(
        total_dependencies=0,
        dependencies_checked=0,
        internal_dependencies=0,
        ignored_dependencies=0,
        total_modules=0,
        cycle_count=cycle_count,
        cycles=tuple(
            # Only the cycle count is relevant to the assessment.
            # Construct valid cycle models through the public model.
            __import__(
                "appy.application.circular_dependency_detection_service",
                fromlist=["CircularDependency"],
            ).CircularDependency(
                cycle_id=f"cycle-{index}",
                modules=(f"module_{index}", f"module_{index}",),
                dependency_count=1,
            )
            for index in range(cycle_count)
        ),
    )


def test_empty_assessment_is_healthy(service):
    result = service.assess()

    assert result.health_score == 100
    assert result.status == DependencyHealthStatus.HEALTHY
    assert result.is_healthy is True
    assert result.has_issues is False
    assert result.finding_count == 0
    assert result.findings == ()


def test_assessment_with_empty_results_is_healthy(service):
    result = service.assess(
        consistency_result(),
        import_result(),
        circular_result(),
    )

    assert result.health_score == 100
    assert result.status == DependencyHealthStatus.HEALTHY
    assert result.findings == ()


def test_valid_internal_imports_produce_healthy_assessment(service):
    result = service.assess(import_reference_result=import_result(valid=5))

    assert result.health_score == 100
    assert result.internal_dependencies == 5
    assert result.invalid_references == 0
    assert result.status == DependencyHealthStatus.HEALTHY


def test_external_imports_are_informational(service):
    result = service.assess(import_reference_result=import_result(external=3))

    assert result.external_dependencies == 3
    assert result.health_score == 100
    assert result.status == DependencyHealthStatus.HEALTHY
    assert result.info_findings[0].code == "EXTERNAL_IMPORT_REFERENCES"


def test_unresolved_imports_reduce_score(service):
    result = service.assess(import_reference_result=import_result(unresolved=2))

    assert result.unresolved_dependencies == 2
    assert result.health_score == 92
    assert result.status == DependencyHealthStatus.NEEDS_ATTENTION
    assert result.warning_findings[0].code == "UNRESOLVED_IMPORT_REFERENCES"


def test_invalid_references_reduce_score(service):
    result = service.assess(import_reference_result=import_result(invalid=2))

    assert result.invalid_references == 2
    assert result.health_score == 70
    assert result.status == DependencyHealthStatus.UNHEALTHY
    assert result.error_findings[0].code == "INVALID_IMPORT_REFERENCES"


def test_consistency_errors_reduce_score(service):
    result = service.assess(
        consistency_result=consistency_result(imports_checked=4, errors=2)
    )

    assert result.consistency_errors == 2
    assert result.health_score == 76
    assert result.status == DependencyHealthStatus.UNHEALTHY
    assert result.error_findings[0].code == "DEPENDENCY_CONSISTENCY_ERRORS"


def test_consistency_warnings_reduce_score(service):
    result = service.assess(
        consistency_result=consistency_result(imports_checked=4, warnings=2)
    )

    assert result.consistency_warnings == 2
    assert result.health_score == 94
    assert result.status == DependencyHealthStatus.NEEDS_ATTENTION
    assert result.warning_findings[0].code == "DEPENDENCY_CONSISTENCY_WARNINGS"


def test_circular_dependencies_are_critical(service):
    result = service.assess(circular_dependency_result=circular_result(2))

    assert result.circular_dependency_count == 2
    assert result.health_score == 60
    assert result.status == DependencyHealthStatus.UNHEALTHY
    assert result.critical_findings[0].code == "CIRCULAR_DEPENDENCIES"


def test_score_is_bounded_at_zero(service):
    result = service.assess(
        consistency_result=consistency_result(errors=10),
        import_reference_result=import_result(invalid=10, unresolved=10),
        circular_dependency_result=circular_result(10),
    )

    assert result.health_score == 0


def test_score_never_exceeds_one_hundred(service):
    result = service.assess(import_reference_result=import_result(external=100))

    assert result.health_score == 100


def test_assessment_combines_all_result_types(service):
    result = service.assess(
        consistency_result=consistency_result(
            imports_checked=5,
            errors=1,
            warnings=1,
        ),
        import_reference_result=import_result(
            valid=3,
            invalid=1,
            unresolved=2,
            external=2,
        ),
        circular_dependency_result=circular_result(1),
    )

    assert result.total_dependencies == 8
    assert result.internal_dependencies == 3
    assert result.external_dependencies == 2
    assert result.unresolved_dependencies == 2
    assert result.invalid_references == 1
    assert result.consistency_errors == 1
    assert result.consistency_warnings == 1
    assert result.circular_dependency_count == 1
    assert result.status == DependencyHealthStatus.UNHEALTHY


def test_total_dependencies_uses_largest_available_count(service):
    result = service.assess(
        consistency_result=consistency_result(imports_checked=8),
        import_reference_result=import_result(valid=3, external=2),
    )

    assert result.total_dependencies == 8


def test_findings_are_sorted_by_severity(service):
    result = service.assess(
        consistency_result=consistency_result(warnings=1, errors=1),
        import_reference_result=import_result(
            invalid=1,
            unresolved=1,
            external=1,
        ),
        circular_dependency_result=circular_result(1),
    )

    severities = [finding.severity for finding in result.findings]
    assert severities == sorted(
        severities,
        key={
            DependencyHealthSeverity.CRITICAL: 0,
            DependencyHealthSeverity.ERROR: 1,
            DependencyHealthSeverity.WARNING: 2,
            DependencyHealthSeverity.INFO: 3,
        }.get,
    )


def test_findings_have_unique_codes(service):
    result = service.assess(
        consistency_result=consistency_result(errors=1, warnings=1),
        import_reference_result=import_result(
            invalid=1,
            unresolved=1,
            external=1,
        ),
        circular_dependency_result=circular_result(1),
    )

    codes = [finding.code for finding in result.findings]
    assert len(codes) == len(set(codes))


def test_critical_findings_property(service):
    result = service.assess(circular_dependency_result=circular_result(2))

    assert len(result.critical_findings) == 1
    assert result.critical_findings[0].affected_count == 2


def test_error_findings_property(service):
    result = service.assess(import_reference_result=import_result(invalid=3))

    assert len(result.error_findings) == 1
    assert result.error_findings[0].affected_count == 3


def test_warning_findings_property(service):
    result = service.assess(import_reference_result=import_result(unresolved=4))

    assert len(result.warning_findings) == 1
    assert result.warning_findings[0].affected_count == 4


def test_info_findings_property(service):
    result = service.assess(import_reference_result=import_result(external=4))

    assert len(result.info_findings) == 1
    assert result.info_findings[0].affected_count == 4


def test_finding_count_matches_findings(service):
    result = service.assess(
        consistency_result=consistency_result(errors=1, warnings=1),
        import_reference_result=import_result(
            invalid=1,
            unresolved=1,
            external=1,
        ),
        circular_dependency_result=circular_result(1),
    )

    assert result.finding_count == len(result.findings)
    assert result.has_issues is True


def test_warning_only_assessment_needs_attention(service):
    result = service.assess(
        import_reference_result=import_result(unresolved=1)
    )

    assert result.status == DependencyHealthStatus.NEEDS_ATTENTION
    assert result.is_healthy is False


def test_error_assessment_is_unhealthy(service):
    result = service.assess(
        consistency_result=consistency_result(errors=1)
    )

    assert result.status == DependencyHealthStatus.UNHEALTHY
    assert result.is_healthy is False


def test_critical_assessment_is_unhealthy_even_with_high_score(service):
    result = service.assess(circular_dependency_result=circular_result(1))

    assert result.status == DependencyHealthStatus.UNHEALTHY
    assert result.health_score == 80


def test_external_imports_do_not_make_assessment_unhealthy(service):
    result = service.assess(import_reference_result=import_result(external=10))

    assert result.status == DependencyHealthStatus.HEALTHY
    assert result.is_healthy is True


@pytest.mark.parametrize(
    "kwargs",
    [
        {"consistency_result": object()},
        {"import_reference_result": object()},
        {"circular_dependency_result": object()},
    ],
)
def test_invalid_result_types_raise_error(service, kwargs):
    with pytest.raises(DependencyHealthAssessmentError):
        service.assess(**kwargs)


def test_all_optional_results_can_be_omitted(service):
    result = service.assess(
        consistency_result=None,
        import_reference_result=None,
        circular_dependency_result=None,
    )

    assert result.health_score == 100
    assert result.status == DependencyHealthStatus.HEALTHY


def test_assessment_model_is_immutable(service):
    result = service.assess()

    with pytest.raises(FrozenInstanceError):
        result.health_score = 50


def test_finding_model_is_immutable():
    finding = DependencyHealthFinding(
        code="TEST",
        message="Test finding.",
        severity=DependencyHealthSeverity.WARNING,
        affected_count=1,
    )

    with pytest.raises(FrozenInstanceError):
        finding.code = "CHANGED"


def test_finding_rejects_empty_code():
    with pytest.raises(DependencyHealthAssessmentError):
        DependencyHealthFinding(
            code="",
            message="Message",
            severity=DependencyHealthSeverity.WARNING,
            affected_count=1,
        )


def test_finding_rejects_empty_message():
    with pytest.raises(DependencyHealthAssessmentError):
        DependencyHealthFinding(
            code="TEST",
            message=" ",
            severity=DependencyHealthSeverity.WARNING,
            affected_count=1,
        )


def test_finding_rejects_invalid_severity():
    with pytest.raises(DependencyHealthAssessmentError):
        DependencyHealthFinding(
            code="TEST",
            message="Message",
            severity="warning",
            affected_count=1,
        )


@pytest.mark.parametrize("count", [0, -1, True, 1.5, "1"])
def test_finding_rejects_invalid_affected_count(count):
    with pytest.raises(DependencyHealthAssessmentError):
        DependencyHealthFinding(
            code="TEST",
            message="Message",
            severity=DependencyHealthSeverity.WARNING,
            affected_count=count,
        )


@pytest.mark.parametrize("score", [-1, 101, True, 1.5, "80"])
def test_assessment_rejects_invalid_score(score):
    with pytest.raises(DependencyHealthAssessmentError):
        DependencyHealthAssessment(
            health_score=score,
            status=DependencyHealthStatus.HEALTHY,
            total_dependencies=0,
            internal_dependencies=0,
            external_dependencies=0,
            unresolved_dependencies=0,
            invalid_references=0,
            consistency_errors=0,
            consistency_warnings=0,
            circular_dependency_count=0,
            findings=(),
        )


def test_assessment_rejects_invalid_status():
    with pytest.raises(DependencyHealthAssessmentError):
        DependencyHealthAssessment(
            health_score=100,
            status="healthy",
            total_dependencies=0,
            internal_dependencies=0,
            external_dependencies=0,
            unresolved_dependencies=0,
            invalid_references=0,
            consistency_errors=0,
            consistency_warnings=0,
            circular_dependency_count=0,
            findings=(),
        )


@pytest.mark.parametrize("count", [-1, True, 1.5, "1"])
def test_assessment_rejects_invalid_counts(count):
    with pytest.raises(DependencyHealthAssessmentError):
        DependencyHealthAssessment(
            health_score=100,
            status=DependencyHealthStatus.HEALTHY,
            total_dependencies=count,
            internal_dependencies=0,
            external_dependencies=0,
            unresolved_dependencies=0,
            invalid_references=0,
            consistency_errors=0,
            consistency_warnings=0,
            circular_dependency_count=0,
            findings=(),
        )


def test_assessment_rejects_non_tuple_findings():
    with pytest.raises(DependencyHealthAssessmentError):
        DependencyHealthAssessment(
            health_score=100,
            status=DependencyHealthStatus.HEALTHY,
            total_dependencies=0,
            internal_dependencies=0,
            external_dependencies=0,
            unresolved_dependencies=0,
            invalid_references=0,
            consistency_errors=0,
            consistency_warnings=0,
            circular_dependency_count=0,
            findings=[],
        )


def test_assessment_rejects_invalid_finding_items():
    with pytest.raises(DependencyHealthAssessmentError):
        DependencyHealthAssessment(
            health_score=100,
            status=DependencyHealthStatus.HEALTHY,
            total_dependencies=0,
            internal_dependencies=0,
            external_dependencies=0,
            unresolved_dependencies=0,
            invalid_references=0,
            consistency_errors=0,
            consistency_warnings=0,
            circular_dependency_count=0,
            findings=(object(),),
        )


def test_assessment_does_not_mutate_input_results(service):
    consistency = consistency_result(imports_checked=3, warnings=1)
    imports = import_result(valid=2, unresolved=1)
    circular = circular_result(0)

    original_consistency_issues = consistency.issues
    original_import_records = imports.records
    original_cycles = circular.cycles

    service.assess(consistency, imports, circular)

    assert consistency.issues == original_consistency_issues
    assert imports.records == original_import_records
    assert circular.cycles == original_cycles


def test_repeated_assessment_is_deterministic(service):
    consistency = consistency_result(errors=1, warnings=1)
    imports = import_result(valid=2, invalid=1, external=1)
    circular = circular_result(1)

    first = service.assess(consistency, imports, circular)
    second = service.assess(consistency, imports, circular)

    assert first == second


def test_result_counts_are_not_inferred_from_external_imports(service):
    result = service.assess(import_reference_result=import_result(external=5))

    assert result.external_dependencies == 5
    assert result.internal_dependencies == 0
    assert result.total_dependencies == 5


def test_consistency_and_import_findings_are_both_preserved(service):
    result = service.assess(
        consistency_result=consistency_result(errors=1),
        import_reference_result=import_result(invalid=2),
    )

    codes = {finding.code for finding in result.findings}
    assert "DEPENDENCY_CONSISTENCY_ERRORS" in codes
    assert "INVALID_IMPORT_REFERENCES" in codes
    assert result.invalid_references == 2
    assert result.consistency_errors == 1


def test_severity_order_is_critical_error_warning_info(service):
    result = service.assess(
        consistency_result=consistency_result(errors=1, warnings=1),
        import_reference_result=import_result(
            invalid=1,
            unresolved=1,
            external=1,
        ),
        circular_dependency_result=circular_result(1),
    )

    assert [item.severity for item in result.findings] == [
        DependencyHealthSeverity.CRITICAL,
        DependencyHealthSeverity.ERROR,
        DependencyHealthSeverity.ERROR,
        DependencyHealthSeverity.WARNING,
        DependencyHealthSeverity.WARNING,
        DependencyHealthSeverity.INFO,
    ]
