
"""Provide application-level execution reliability and error handling."""

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from threading import RLock
from typing import Any


class ApplicationReliabilityError(ValueError):
    """Raised when reliability tracking or execution fails."""

    def __init__(
        self,
        message: str,
        stage: str = "reliability",
        original_error: Exception | None = None,
    ) -> None:
        super().__init__(message)
        self.stage = stage
        self.original_error = original_error


@dataclass(frozen=True)
class ApplicationExecutionRecord:
    """Immutable record of one application execution."""

    execution_id: int
    operation: str
    successful: bool
    stage: str
    started_at: datetime
    completed_at: datetime
    duration_seconds: float
    error_type: str | None = None
    error_message: str | None = None

    def __post_init__(self) -> None:
        if (
            isinstance(self.execution_id, bool)
            or not isinstance(self.execution_id, int)
            or self.execution_id <= 0
        ):
            raise ValueError("execution_id must be a positive integer")

        if not isinstance(self.operation, str) or not self.operation.strip():
            raise ValueError("operation must be a non-empty string")

        if not isinstance(self.successful, bool):
            raise ValueError("successful must be a boolean")

        if not isinstance(self.stage, str) or not self.stage.strip():
            raise ValueError("stage must be a non-empty string")

        if not isinstance(self.started_at, datetime):
            raise ValueError("started_at must be a datetime")

        if not isinstance(self.completed_at, datetime):
            raise ValueError("completed_at must be a datetime")

        if (
            isinstance(self.duration_seconds, bool)
            or not isinstance(self.duration_seconds, (int, float))
            or self.duration_seconds < 0
        ):
            raise ValueError("duration_seconds must be a non-negative number")

        if self.successful and (
            self.error_type is not None or self.error_message is not None
        ):
            raise ValueError("Successful executions cannot contain error details")

        if not self.successful and (
            not isinstance(self.error_type, str)
            or not self.error_type.strip()
            or not isinstance(self.error_message, str)
            or not self.error_message.strip()
        ):
            raise ValueError("Failed executions must contain error details")


@dataclass(frozen=True)
class ApplicationReliabilitySummary:
    """Aggregated application execution reliability statistics."""

    total_executions: int
    successful_executions: int
    failed_executions: int
    success_rate: float
    failure_rate: float
    average_duration_seconds: float
    records: tuple[ApplicationExecutionRecord, ...]

    @property
    def is_reliable(self) -> bool:
        """Return whether all recorded executions succeeded."""

        return self.total_executions > 0 and self.failed_executions == 0

    @property
    def failed_records(self) -> tuple[ApplicationExecutionRecord, ...]:
        return tuple(record for record in self.records if not record.successful)

    @property
    def successful_records(self) -> tuple[ApplicationExecutionRecord, ...]:
        return tuple(record for record in self.records if record.successful)


class ApplicationReliabilityErrorHandlingService:
    """Execute operations and maintain a thread-safe reliability history."""

    def __init__(self, max_records: int = 1000) -> None:
        if (
            isinstance(max_records, bool)
            or not isinstance(max_records, int)
            or max_records <= 0
        ):
            raise ValueError("max_records must be a positive integer")

        self.max_records = max_records
        self._records: list[ApplicationExecutionRecord] = []
        self._next_execution_id = 1
        self._lock = RLock()

    def execute(
        self,
        operation: str,
        callback: Callable[..., Any],
        *args: Any,
        stage: str = "execution",
        **kwargs: Any,
    ) -> Any:
        """Execute a callback, record its outcome, and preserve its exception."""

        if not isinstance(operation, str) or not operation.strip():
            raise ApplicationReliabilityError(
                "operation must be a non-empty string.",
                stage="validation",
            )

        if not callable(callback):
            raise ApplicationReliabilityError(
                "callback must be callable.",
                stage="validation",
            )

        if not isinstance(stage, str) or not stage.strip():
            raise ApplicationReliabilityError(
                "stage must be a non-empty string.",
                stage="validation",
            )

        started_at = datetime.now(timezone.utc)

        try:
            result = callback(*args, **kwargs)
        except Exception as exc:
            completed_at = datetime.now(timezone.utc)
            self._record_execution(
                operation=operation,
                successful=False,
                stage=stage,
                started_at=started_at,
                completed_at=completed_at,
                error_type=type(exc).__name__,
                error_message=str(exc) or type(exc).__name__,
            )
            raise
        else:
            completed_at = datetime.now(timezone.utc)
            self._record_execution(
                operation=operation,
                successful=True,
                stage=stage,
                started_at=started_at,
                completed_at=completed_at,
            )
            return result

    def record_success(
        self,
        operation: str,
        stage: str = "execution",
        duration_seconds: float = 0.0,
    ) -> ApplicationExecutionRecord:
        """Record a successful operation that was executed elsewhere."""

        return self._record_manual(
            operation=operation,
            successful=True,
            stage=stage,
            duration_seconds=duration_seconds,
        )

    def record_failure(
        self,
        operation: str,
        error: Exception,
        stage: str = "execution",
        duration_seconds: float = 0.0,
    ) -> ApplicationExecutionRecord:
        """Record a failure that occurred outside this service."""

        if not isinstance(error, Exception):
            raise ApplicationReliabilityError(
                "error must be an Exception instance.",
                stage="validation",
            )

        return self._record_manual(
            operation=operation,
            successful=False,
            stage=stage,
            duration_seconds=duration_seconds,
            error_type=type(error).__name__,
            error_message=str(error) or type(error).__name__,
        )

    def get_records(
        self,
        operation: str | None = None,
        successful: bool | None = None,
        limit: int | None = None,
    ) -> tuple[ApplicationExecutionRecord, ...]:
        """Return execution records with optional filters."""

        if operation is not None and (
            not isinstance(operation, str) or not operation.strip()
        ):
            raise ApplicationReliabilityError(
                "operation filter must be a non-empty string.",
                stage="validation",
            )

        if successful is not None and not isinstance(successful, bool):
            raise ApplicationReliabilityError(
                "successful filter must be a boolean or None.",
                stage="validation",
            )

        if limit is not None and (
            isinstance(limit, bool)
            or not isinstance(limit, int)
            or limit < 0
        ):
            raise ApplicationReliabilityError(
                "limit must be a non-negative integer or None.",
                stage="validation",
            )

        with self._lock:
            records = tuple(self._records)

        if operation is not None:
            records = tuple(
                record for record in records if record.operation == operation
            )

        if successful is not None:
            records = tuple(
                record for record in records if record.successful is successful
            )

        if limit is not None:
            records = records[-limit:] if limit else ()

        return records

    def get_summary(self) -> ApplicationReliabilitySummary:
        """Calculate reliability statistics from retained execution records."""

        records = self.get_records()
        total = len(records)
        successful_count = sum(record.successful for record in records)
        failed_count = total - successful_count

        success_rate = (
            successful_count / total * 100.0 if total else 0.0
        )
        failure_rate = failed_count / total * 100.0 if total else 0.0
        average_duration = (
            sum(record.duration_seconds for record in records) / total
            if total
            else 0.0
        )

        return ApplicationReliabilitySummary(
            total_executions=total,
            successful_executions=successful_count,
            failed_executions=failed_count,
            success_rate=success_rate,
            failure_rate=failure_rate,
            average_duration_seconds=average_duration,
            records=records,
        )

    def clear_records(self) -> int:
        """Clear retained execution history and return the removed count."""

        with self._lock:
            removed_count = len(self._records)
            self._records.clear()
            return removed_count

    def _record_manual(
        self,
        operation: str,
        successful: bool,
        stage: str,
        duration_seconds: float,
        error_type: str | None = None,
        error_message: str | None = None,
    ) -> ApplicationExecutionRecord:
        """Validate and record an externally executed operation."""

        if not isinstance(operation, str) or not operation.strip():
            raise ApplicationReliabilityError(
                "operation must be a non-empty string.",
                stage="validation",
            )

        if not isinstance(stage, str) or not stage.strip():
            raise ApplicationReliabilityError(
                "stage must be a non-empty string.",
                stage="validation",
            )

        if (
            isinstance(duration_seconds, bool)
            or not isinstance(duration_seconds, (int, float))
            or duration_seconds < 0
        ):
            raise ApplicationReliabilityError(
                "duration_seconds must be a non-negative number.",
                stage="validation",
            )

        completed_at = datetime.now(timezone.utc)
        started_at = datetime.fromtimestamp(
            completed_at.timestamp() - duration_seconds,
            tz=timezone.utc,
        )

        return self._append_record(
            operation=operation,
            successful=successful,
            stage=stage,
            started_at=started_at,
            completed_at=completed_at,
            duration_seconds=float(duration_seconds),
            error_type=error_type,
            error_message=error_message,
        )

    def _record_execution(
        self,
        operation: str,
        successful: bool,
        stage: str,
        started_at: datetime,
        completed_at: datetime,
        error_type: str | None = None,
        error_message: str | None = None,
    ) -> ApplicationExecutionRecord:
        """Build and append a record for a callback execution."""

        duration = max(
            0.0,
            (completed_at - started_at).total_seconds(),
        )

        return self._append_record(
            operation=operation,
            successful=successful,
            stage=stage,
            started_at=started_at,
            completed_at=completed_at,
            duration_seconds=duration,
            error_type=error_type,
            error_message=error_message,
        )

    def _append_record(
        self,
        operation: str,
        successful: bool,
        stage: str,
        started_at: datetime,
        completed_at: datetime,
        duration_seconds: float,
        error_type: str | None = None,
        error_message: str | None = None,
    ) -> ApplicationExecutionRecord:
        """Append one record while enforcing the configured history limit."""

        with self._lock:
            record = ApplicationExecutionRecord(
                execution_id=self._next_execution_id,
                operation=operation,
                successful=successful,
                stage=stage,
                started_at=started_at,
                completed_at=completed_at,
                duration_seconds=duration_seconds,
                error_type=error_type,
                error_message=error_message,
            )

            self._next_execution_id += 1
            self._records.append(record)

            if len(self._records) > self.max_records:
                self._records = self._records[-self.max_records:]

            return record
