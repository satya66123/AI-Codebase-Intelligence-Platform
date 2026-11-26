
"""Tests for application reliability and error handling."""

from datetime import datetime, timezone

import pytest

from appy.application.application_reliability_error_handling_service import (
    ApplicationExecutionRecord,
    ApplicationReliabilityError,
    ApplicationReliabilityErrorHandlingService,
    ApplicationReliabilitySummary,
)


@pytest.fixture
def service():
    return ApplicationReliabilityErrorHandlingService()


def test_constructor_uses_default_record_limit():
    instance = ApplicationReliabilityErrorHandlingService()

    assert instance.max_records == 1000


@pytest.mark.parametrize("max_records", [0, -1, True, 1.5, "10"])
def test_constructor_rejects_invalid_record_limit(max_records):
    with pytest.raises(ValueError):
        ApplicationReliabilityErrorHandlingService(max_records=max_records)


def test_execute_returns_callback_result(service):
    result = service.execute("sample", lambda: "completed")

    assert result == "completed"


def test_execute_passes_positional_arguments(service):
    result = service.execute("sum", lambda a, b: a + b, 3, 4)

    assert result == 7


def test_execute_passes_keyword_arguments(service):
    result = service.execute(
        "greeting",
        lambda name: f"Hello {name}",
        name="Developer",
    )

    assert result == "Hello Developer"


def test_execute_records_success(service):
    service.execute("sample", lambda: "ok")

    records = service.get_records()

    assert len(records) == 1
    assert records[0].successful is True
    assert records[0].operation == "sample"


def test_execute_records_custom_stage(service):
    service.execute("analysis", lambda: True, stage="analysis_pipeline")

    assert service.get_records()[0].stage == "analysis_pipeline"


def test_execute_preserves_callback_exception(service):
    original_error = RuntimeError("provider unavailable")

    with pytest.raises(RuntimeError) as exc_info:
        service.execute(
            "provider_call",
            lambda: (_ for _ in ()).throw(original_error),
            stage="provider",
        )

    assert exc_info.value is original_error


def test_execute_records_failure_details(service):
    with pytest.raises(RuntimeError):
        service.execute(
            "provider_call",
            lambda: (_ for _ in ()).throw(RuntimeError("provider unavailable")),
            stage="provider",
        )

    record = service.get_records()[0]

    assert record.successful is False
    assert record.stage == "provider"
    assert record.error_type == "RuntimeError"
    assert record.error_message == "provider unavailable"


def test_execute_records_empty_exception_message(service):
    class EmptyMessageError(Exception):
        pass

    with pytest.raises(EmptyMessageError):
        service.execute(
            "operation",
            lambda: (_ for _ in ()).throw(EmptyMessageError()),
        )

    assert service.get_records()[0].error_message == "EmptyMessageError"


def test_execute_rejects_empty_operation(service):
    with pytest.raises(ApplicationReliabilityError) as exc_info:
        service.execute("", lambda: None)

    assert exc_info.value.stage == "validation"


def test_execute_rejects_non_callable_callback(service):
    with pytest.raises(ApplicationReliabilityError):
        service.execute("operation", None)


def test_execute_rejects_empty_stage(service):
    with pytest.raises(ApplicationReliabilityError):
        service.execute("operation", lambda: None, stage=" ")


def test_execute_does_not_record_invalid_callback(service):
    with pytest.raises(ApplicationReliabilityError):
        service.execute("operation", None)

    assert service.get_records() == ()


def test_record_success_creates_successful_record(service):
    record = service.record_success(
        "repository_analysis",
        stage="analysis",
        duration_seconds=1.5,
    )

    assert record.successful is True
    assert record.operation == "repository_analysis"
    assert record.stage == "analysis"
    assert record.duration_seconds == 1.5
    assert record.error_type is None


def test_record_failure_creates_failed_record(service):
    record = service.record_failure(
        "provider_request",
        RuntimeError("timeout"),
        stage="provider",
        duration_seconds=2.0,
    )

    assert record.successful is False
    assert record.error_type == "RuntimeError"
    assert record.error_message == "timeout"
    assert record.duration_seconds == 2.0


def test_record_failure_rejects_non_exception(service):
    with pytest.raises(ApplicationReliabilityError):
        service.record_failure("operation", "not an exception")


@pytest.mark.parametrize("operation", ["", " "])
def test_record_success_rejects_invalid_operation(service, operation):
    with pytest.raises(ApplicationReliabilityError):
        service.record_success(operation)


@pytest.mark.parametrize("stage", ["", " "])
def test_record_success_rejects_invalid_stage(service, stage):
    with pytest.raises(ApplicationReliabilityError):
        service.record_success("operation", stage=stage)


@pytest.mark.parametrize("duration", [-1, True, 1.5 if False else "1"])
def test_record_success_rejects_invalid_duration(service, duration):
    with pytest.raises(ApplicationReliabilityError):
        service.record_success("operation", duration_seconds=duration)


def test_record_failure_rejects_negative_duration(service):
    with pytest.raises(ApplicationReliabilityError):
        service.record_failure(
            "operation",
            RuntimeError("failure"),
            duration_seconds=-1,
        )


def test_get_records_returns_all_records(service):
    service.record_success("first")
    service.record_failure("second", RuntimeError("failed"))

    assert len(service.get_records()) == 2


def test_get_records_filters_by_operation(service):
    service.record_success("analysis")
    service.record_success("export")

    records = service.get_records(operation="analysis")

    assert len(records) == 1
    assert records[0].operation == "analysis"


def test_get_records_filters_by_success_status(service):
    service.record_success("success")
    service.record_failure("failure", RuntimeError("failed"))

    records = service.get_records(successful=False)

    assert len(records) == 1
    assert records[0].successful is False


def test_get_records_applies_limit(service):
    service.record_success("first")
    service.record_success("second")
    service.record_success("third")

    records = service.get_records(limit=2)

    assert len(records) == 2
    assert records[0].operation == "second"
    assert records[1].operation == "third"


def test_get_records_zero_limit_returns_empty_tuple(service):
    service.record_success("first")

    assert service.get_records(limit=0) == ()


def test_get_records_rejects_invalid_operation_filter(service):
    with pytest.raises(ApplicationReliabilityError):
        service.get_records(operation=" ")


def test_get_records_rejects_invalid_success_filter(service):
    with pytest.raises(ApplicationReliabilityError):
        service.get_records(successful="yes")


@pytest.mark.parametrize("limit", [-1, True, 1.5, "2"])
def test_get_records_rejects_invalid_limit(service, limit):
    with pytest.raises(ApplicationReliabilityError):
        service.get_records(limit=limit)


def test_get_summary_counts_successful_and_failed(service):
    service.record_success("first")
    service.record_success("second")
    service.record_failure("third", RuntimeError("failed"))

    summary = service.get_summary()

    assert isinstance(summary, ApplicationReliabilitySummary)
    assert summary.total_executions == 3
    assert summary.successful_executions == 2
    assert summary.failed_executions == 1


def test_get_summary_calculates_success_and_failure_rates(service):
    service.record_success("first")
    service.record_failure("second", RuntimeError("failed"))

    summary = service.get_summary()

    assert summary.success_rate == 50.0
    assert summary.failure_rate == 50.0


def test_get_summary_calculates_average_duration(service):
    service.record_success("first", duration_seconds=2.0)
    service.record_success("second", duration_seconds=4.0)

    summary = service.get_summary()

    assert summary.average_duration_seconds == 3.0


def test_get_summary_empty_history_has_zero_values(service):
    summary = service.get_summary()

    assert summary.total_executions == 0
    assert summary.success_rate == 0.0
    assert summary.failure_rate == 0.0
    assert summary.average_duration_seconds == 0.0
    assert summary.is_reliable is False


def test_get_summary_exposes_failed_and_successful_records(service):
    service.record_success("first")
    service.record_failure("second", RuntimeError("failed"))

    summary = service.get_summary()

    assert len(summary.successful_records) == 1
    assert len(summary.failed_records) == 1


def test_is_reliable_when_all_executions_succeed(service):
    service.record_success("first")
    service.record_success("second")

    assert service.get_summary().is_reliable is True


def test_is_not_reliable_when_any_execution_fails(service):
    service.record_success("first")
    service.record_failure("second", RuntimeError("failed"))

    assert service.get_summary().is_reliable is False


def test_history_limit_removes_oldest_records():
    instance = ApplicationReliabilityErrorHandlingService(max_records=2)

    instance.record_success("first")
    instance.record_success("second")
    instance.record_success("third")

    records = instance.get_records()

    assert len(records) == 2
    assert tuple(record.operation for record in records) == (
        "second",
        "third",
    )


def test_execution_ids_remain_incremental_after_trimming():
    instance = ApplicationReliabilityErrorHandlingService(max_records=1)

    first = instance.record_success("first")
    second = instance.record_success("second")

    assert first.execution_id == 1
    assert second.execution_id == 2


def test_clear_records_returns_removed_count(service):
    service.record_success("first")
    service.record_success("second")

    removed = service.clear_records()

    assert removed == 2
    assert service.get_records() == ()


def test_clear_records_does_not_reset_execution_ids(service):
    first = service.record_success("first")
    service.clear_records()
    second = service.record_success("second")

    assert first.execution_id == 1
    assert second.execution_id == 2


def test_execution_records_have_timezone_aware_timestamps(service):
    service.execute("operation", lambda: None)

    record = service.get_records()[0]

    assert record.started_at.tzinfo is not None
    assert record.completed_at.tzinfo is not None
    assert record.started_at.utcoffset() == timezone.utc.utcoffset(record.started_at)


def test_execution_record_is_immutable(service):
    record = service.record_success("operation")

    with pytest.raises(AttributeError):
        record.operation = "changed"


def test_execution_record_rejects_invalid_execution_id():
    now = datetime.now(timezone.utc)

    with pytest.raises(ValueError):
        ApplicationExecutionRecord(
            execution_id=0,
            operation="operation",
            successful=True,
            stage="execution",
            started_at=now,
            completed_at=now,
            duration_seconds=0.0,
        )


def test_execution_record_rejects_success_with_error_details():
    now = datetime.now(timezone.utc)

    with pytest.raises(ValueError):
        ApplicationExecutionRecord(
            execution_id=1,
            operation="operation",
            successful=True,
            stage="execution",
            started_at=now,
            completed_at=now,
            duration_seconds=0.0,
            error_type="RuntimeError",
            error_message="failure",
        )


def test_execution_record_rejects_failure_without_error_details():
    now = datetime.now(timezone.utc)

    with pytest.raises(ValueError):
        ApplicationExecutionRecord(
            execution_id=1,
            operation="operation",
            successful=False,
            stage="execution",
            started_at=now,
            completed_at=now,
            duration_seconds=0.0,
        )


def test_execution_record_rejects_negative_duration():
    now = datetime.now(timezone.utc)

    with pytest.raises(ValueError):
        ApplicationExecutionRecord(
            execution_id=1,
            operation="operation",
            successful=True,
            stage="execution",
            started_at=now,
            completed_at=now,
            duration_seconds=-1,
        )


def test_records_are_returned_as_immutable_tuple(service):
    service.record_success("operation")

    records = service.get_records()

    assert isinstance(records, tuple)


def test_multiple_executions_receive_unique_ids(service):
    service.record_success("first")
    service.record_success("second")
    service.record_success("third")

    ids = tuple(record.execution_id for record in service.get_records())

    assert ids == (1, 2, 3)
