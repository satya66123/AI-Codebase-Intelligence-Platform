
"""Tests for the release readiness and final validation service."""

from dataclasses import FrozenInstanceError

import pytest

from appy.application.release_readiness_final_validation_service import (
    ReleaseReadinessCheck,
    ReleaseReadinessError,
    ReleaseReadinessFinalValidationService,
    ReleaseReadinessReport,
)


@pytest.fixture
def service():
    return ReleaseReadinessFinalValidationService()


@pytest.fixture
def project_info():
    return {
        "project_name": "AI Codebase Intelligence Platform",
        "version": "1.0.0",
    }


@pytest.fixture
def phases():
    return [
        {"name": "Phase 0", "status": "Completed"},
        {"name": "Phase 1", "status": "Completed"},
        {"name": "Phase 2", "status": "Completed"},
        {"name": "Phase 3", "status": "Completed"},
        {"name": "Phase 4", "status": "Completed"},
    ]


@pytest.fixture
def components():
    return [
        {"name": "Knowledge Service", "status": "Completed"},
        {"name": "Analysis Service", "status": "Completed"},
        {"name": "Validation Service", "status": "Completed"},
    ]


@pytest.fixture
def test_summary():
    return {
        "tests_passed": 100,
        "tests_failed": 0,
    }


@pytest.fixture
def valid_report_inputs(
    project_info,
    phases,
    components,
    test_summary,
):
    return {
        "project_info": project_info,
        "phases": phases,
        "components": components,
        "test_summary": test_summary,
        "provider_validation_passed": True,
        "reliability_failure_count": 0,
        "documentation_complete": True,
    }


def test_validate_returns_release_readiness_report(
    service,
    valid_report_inputs,
):
    result = service.validate(**valid_report_inputs)

    assert isinstance(result, ReleaseReadinessReport)


def test_validate_uses_project_name(service, valid_report_inputs):
    result = service.validate(**valid_report_inputs)

    assert result.project_name == "AI Codebase Intelligence Platform"


def test_validate_creates_seven_required_checks(
    service,
    valid_report_inputs,
):
    result = service.validate(**valid_report_inputs)

    assert result.total_checks == 7


def test_validate_includes_all_required_check_names(
    service,
    valid_report_inputs,
):
    result = service.validate(**valid_report_inputs)

    names = {check.name for check in result.checks}

    assert names == {
        "Project metadata",
        "Development phases",
        "Implemented components",
        "Test validation",
        "Provider integration",
        "Application reliability",
        "Final documentation",
    }


def test_validate_returns_ready_when_all_checks_pass(
    service,
    valid_report_inputs,
):
    result = service.validate(**valid_report_inputs)

    assert result.is_ready is True
    assert result.status == "READY"


def test_validate_counts_all_passed_checks(
    service,
    valid_report_inputs,
):
    result = service.validate(**valid_report_inputs)

    assert result.passed_checks == 7
    assert result.failed_checks == 0


def test_validate_calculates_readiness_percentage(
    service,
    valid_report_inputs,
):
    result = service.validate(**valid_report_inputs)

    assert result.readiness_percentage == 100.0


def test_validate_returns_timezone_aware_iso_timestamp(
    service,
    valid_report_inputs,
):
    from datetime import datetime

    result = service.validate(**valid_report_inputs)
    timestamp = datetime.fromisoformat(result.generated_at)

    assert timestamp.tzinfo is not None
    assert timestamp.utcoffset().total_seconds() == 0


def test_validate_returns_immutable_checks(
    service,
    valid_report_inputs,
):
    result = service.validate(**valid_report_inputs)

    assert isinstance(result.checks, tuple)


def test_validate_rejects_invalid_project_info(
    service,
    valid_report_inputs,
):
    valid_report_inputs["project_info"] = None

    with pytest.raises(ReleaseReadinessError):
        service.validate(**valid_report_inputs)


@pytest.mark.parametrize(
    "project_info",
    [
        {},
        {"version": "1.0.0"},
        {"project_name": "Project"},
        {"project_name": "", "version": "1.0.0"},
        {"project_name": "Project", "version": " "},
    ],
)
def test_validate_rejects_missing_project_metadata(
    service,
    valid_report_inputs,
    project_info,
):
    valid_report_inputs["project_info"] = project_info

    with pytest.raises(ReleaseReadinessError):
        service.validate(**valid_report_inputs)


@pytest.mark.parametrize(
    "phases",
    [
        None,
        [],
        "Phase 1",
        {},
    ],
)
def test_validate_rejects_invalid_phases(
    service,
    valid_report_inputs,
    phases,
):
    valid_report_inputs["phases"] = phases

    with pytest.raises(ReleaseReadinessError):
        service.validate(**valid_report_inputs)


@pytest.mark.parametrize(
    "components",
    [
        None,
        [],
        "Component",
        {},
    ],
)
def test_validate_rejects_invalid_components(
    service,
    valid_report_inputs,
    components,
):
    valid_report_inputs["components"] = components

    with pytest.raises(ReleaseReadinessError):
        service.validate(**valid_report_inputs)


@pytest.mark.parametrize(
    "item",
    [
        None,
        {},
        {"status": "Completed"},
        {"name": "Phase 1"},
        {"name": " ", "status": "Completed"},
        {"name": "Phase 1", "status": " "},
    ],
)
def test_validate_rejects_invalid_phase_entries(
    service,
    valid_report_inputs,
    item,
):
    valid_report_inputs["phases"] = [item]

    with pytest.raises(ReleaseReadinessError):
        service.validate(**valid_report_inputs)


@pytest.mark.parametrize(
    "item",
    [
        None,
        {},
        {"status": "Completed"},
        {"name": "Component"},
        {"name": " ", "status": "Completed"},
        {"name": "Component", "status": " "},
    ],
)
def test_validate_rejects_invalid_component_entries(
    service,
    valid_report_inputs,
    item,
):
    valid_report_inputs["components"] = [item]

    with pytest.raises(ReleaseReadinessError):
        service.validate(**valid_report_inputs)


def test_validate_rejects_invalid_test_summary(
    service,
    valid_report_inputs,
):
    valid_report_inputs["test_summary"] = None

    with pytest.raises(ReleaseReadinessError):
        service.validate(**valid_report_inputs)


@pytest.mark.parametrize(
    "test_summary",
    [
        {},
        {"tests_passed": -1, "tests_failed": 0},
        {"tests_passed": 10, "tests_failed": -1},
        {"tests_passed": True, "tests_failed": 0},
        {"tests_passed": 10, "tests_failed": False},
        {"tests_passed": "10", "tests_failed": 0},
        {"tests_passed": 10, "tests_failed": "0"},
    ],
)
def test_validate_rejects_invalid_test_counts(
    service,
    valid_report_inputs,
    test_summary,
):
    valid_report_inputs["test_summary"] = test_summary

    with pytest.raises(ReleaseReadinessError):
        service.validate(**valid_report_inputs)


def test_validate_rejects_non_boolean_provider_result(
    service,
    valid_report_inputs,
):
    valid_report_inputs["provider_validation_passed"] = "yes"

    with pytest.raises(ReleaseReadinessError):
        service.validate(**valid_report_inputs)


@pytest.mark.parametrize(
    "failure_count",
    [-1, True, 1.5, "0", None],
)
def test_validate_rejects_invalid_reliability_failure_count(
    service,
    valid_report_inputs,
    failure_count,
):
    valid_report_inputs["reliability_failure_count"] = failure_count

    with pytest.raises(ReleaseReadinessError):
        service.validate(**valid_report_inputs)


def test_validate_rejects_non_boolean_documentation_result(
    service,
    valid_report_inputs,
):
    valid_report_inputs["documentation_complete"] = "complete"

    with pytest.raises(ReleaseReadinessError):
        service.validate(**valid_report_inputs)


def test_validate_fails_for_incomplete_phase(
    service,
    valid_report_inputs,
):
    valid_report_inputs["phases"][2]["status"] = "In progress"

    result = service.validate(**valid_report_inputs)

    assert result.is_ready is False
    assert "Development phases" in result.failed_check_names


def test_validate_fails_for_incomplete_component(
    service,
    valid_report_inputs,
):
    valid_report_inputs["components"][1]["status"] = "Pending"

    result = service.validate(**valid_report_inputs)

    assert result.is_ready is False
    assert "Implemented components" in result.failed_check_names


@pytest.mark.parametrize(
    "status",
    ["Completed", "completed", "COMPLETE", "Complete"],
)
def test_validate_accepts_completed_status_variations(
    service,
    valid_report_inputs,
    status,
):
    valid_report_inputs["phases"] = [
        {"name": "Phase 1", "status": status}
    ]

    result = service.validate(**valid_report_inputs)

    assert result.checks[1].passed is True


def test_validate_fails_when_tests_have_failures(
    service,
    valid_report_inputs,
):
    valid_report_inputs["test_summary"] = {
        "tests_passed": 99,
        "tests_failed": 1,
    }

    result = service.validate(**valid_report_inputs)

    assert result.is_ready is False
    assert "Test validation" in result.failed_check_names


def test_validate_fails_when_no_tests_were_executed(
    service,
    valid_report_inputs,
):
    valid_report_inputs["test_summary"] = {
        "tests_passed": 0,
        "tests_failed": 0,
    }

    result = service.validate(**valid_report_inputs)

    assert result.is_ready is False


def test_validate_fails_when_provider_validation_fails(
    service,
    valid_report_inputs,
):
    valid_report_inputs["provider_validation_passed"] = False

    result = service.validate(**valid_report_inputs)

    assert result.is_ready is False
    assert "Provider integration" in result.failed_check_names


def test_validate_fails_when_reliability_errors_exist(
    service,
    valid_report_inputs,
):
    valid_report_inputs["reliability_failure_count"] = 2

    result = service.validate(**valid_report_inputs)

    assert result.is_ready is False
    assert "Application reliability" in result.failed_check_names


def test_validate_fails_when_documentation_is_incomplete(
    service,
    valid_report_inputs,
):
    valid_report_inputs["documentation_complete"] = False

    result = service.validate(**valid_report_inputs)

    assert result.is_ready is False
    assert "Final documentation" in result.failed_check_names


def test_validate_reports_multiple_failed_checks(
    service,
    valid_report_inputs,
):
    valid_report_inputs["phases"][0]["status"] = "Pending"
    valid_report_inputs["test_summary"]["tests_failed"] = 2
    valid_report_inputs["provider_validation_passed"] = False
    valid_report_inputs["reliability_failure_count"] = 1
    valid_report_inputs["documentation_complete"] = False

    result = service.validate(**valid_report_inputs)

    assert result.is_ready is False
    assert result.failed_checks == 5
    assert result.passed_checks == 2


def test_validate_calculates_partial_readiness_percentage(
    service,
    valid_report_inputs,
):
    valid_report_inputs["documentation_complete"] = False

    result = service.validate(**valid_report_inputs)

    assert result.readiness_percentage == 85.71


def test_validate_returns_failed_check_details(
    service,
    valid_report_inputs,
):
    valid_report_inputs["provider_validation_passed"] = False

    result = service.validate(**valid_report_inputs)

    failed_check = next(
        check
        for check in result.checks
        if check.name == "Provider integration"
    )

    assert failed_check.passed is False
    assert "failed" in failed_check.details.lower()


def test_validate_does_not_modify_input_data(
    service,
    valid_report_inputs,
):
    original_name = valid_report_inputs["project_info"]["project_name"]
    original_phase_status = valid_report_inputs["phases"][0]["status"]

    service.validate(**valid_report_inputs)

    assert valid_report_inputs["project_info"]["project_name"] == original_name
    assert valid_report_inputs["phases"][0]["status"] == original_phase_status


def test_check_rejects_empty_name():
    with pytest.raises(ValueError):
        ReleaseReadinessCheck(
            name=" ",
            passed=True,
            details="Valid details.",
        )


def test_check_rejects_non_boolean_result():
    with pytest.raises(ValueError):
        ReleaseReadinessCheck(
            name="Provider integration",
            passed="yes",
            details="Valid details.",
        )


def test_check_rejects_empty_details():
    with pytest.raises(ValueError):
        ReleaseReadinessCheck(
            name="Provider integration",
            passed=True,
            details=" ",
        )


def test_check_is_immutable():
    check = ReleaseReadinessCheck(
        name="Provider integration",
        passed=True,
        details="Validation passed.",
    )

    with pytest.raises(FrozenInstanceError):
        check.passed = False


def test_report_is_immutable(service, valid_report_inputs):
    result = service.validate(**valid_report_inputs)

    with pytest.raises(FrozenInstanceError):
        result.project_name = "Changed"


def test_report_failed_check_names_are_a_tuple(
    service,
    valid_report_inputs,
):
    valid_report_inputs["documentation_complete"] = False

    result = service.validate(**valid_report_inputs)

    assert isinstance(result.failed_check_names, tuple)


def test_report_status_is_not_ready_when_check_fails(
    service,
    valid_report_inputs,
):
    valid_report_inputs["reliability_failure_count"] = 1

    result = service.validate(**valid_report_inputs)

    assert result.status == "NOT READY"
