from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from statistics import mean
from typing import Iterable


class AnalysisPipelineReliabilityError(ValueError):
    """Raised when pipeline reliability monitoring receives invalid input."""


class PipelineStageStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class ReliabilitySeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


@dataclass(frozen=True)
class PipelineStageExecution:
    stage_name: str
    status: PipelineStageStatus
    duration_seconds: float | None = None
    attempt: int = 1
    error_message: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.stage_name, str) or not self.stage_name.strip():
            raise AnalysisPipelineReliabilityError(
                "stage_name must be a non-empty string."
            )

        if not isinstance(self.status, PipelineStageStatus):
            raise AnalysisPipelineReliabilityError(
                "status must be a PipelineStageStatus value."
            )

        if self.duration_seconds is not None:
            if (
                isinstance(self.duration_seconds, bool)
                or not isinstance(self.duration_seconds, (int, float))
                or self.duration_seconds < 0
            ):
                raise AnalysisPipelineReliabilityError(
                    "duration_seconds must be a non-negative number or None."
                )

        if (
            isinstance(self.attempt, bool)
            or not isinstance(self.attempt, int)
            or self.attempt < 1
        ):
            raise AnalysisPipelineReliabilityError(
                "attempt must be a positive integer."
            )

        if not isinstance(self.error_message, str):
            raise AnalysisPipelineReliabilityError(
                "error_message must be a string."
            )

        if self.status is PipelineStageStatus.FAILED and not self.error_message.strip():
            raise AnalysisPipelineReliabilityError(
                "Failed stages must include an error_message."
            )


@dataclass(frozen=True)
class PipelineExecution:
    pipeline_id: str
    stages: tuple[PipelineStageExecution, ...]
    expected_stages: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.pipeline_id, str) or not self.pipeline_id.strip():
            raise AnalysisPipelineReliabilityError(
                "pipeline_id must be a non-empty string."
            )

        if not isinstance(self.stages, tuple) or not all(
            isinstance(stage, PipelineStageExecution) for stage in self.stages
        ):
            raise AnalysisPipelineReliabilityError(
                "stages must be a tuple of PipelineStageExecution objects."
            )

        if not isinstance(self.expected_stages, tuple) or not all(
            isinstance(name, str) and name.strip()
            for name in self.expected_stages
        ):
            raise AnalysisPipelineReliabilityError(
                "expected_stages must be a tuple of non-empty strings."
            )

        if len(self.expected_stages) != len(set(self.expected_stages)):
            raise AnalysisPipelineReliabilityError(
                "expected_stages cannot contain duplicates."
            )


@dataclass(frozen=True)
class PipelineReliabilityIssue:
    code: str
    severity: ReliabilitySeverity
    pipeline_id: str
    message: str
    stage_name: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.code, str) or not self.code.strip():
            raise AnalysisPipelineReliabilityError(
                "Issue code must be a non-empty string."
            )
        if not isinstance(self.severity, ReliabilitySeverity):
            raise AnalysisPipelineReliabilityError(
                "Issue severity must be a ReliabilitySeverity value."
            )
        if not isinstance(self.pipeline_id, str) or not self.pipeline_id.strip():
            raise AnalysisPipelineReliabilityError(
                "Issue pipeline_id must be a non-empty string."
            )
        if not isinstance(self.message, str) or not self.message.strip():
            raise AnalysisPipelineReliabilityError(
                "Issue message must be a non-empty string."
            )
        if not isinstance(self.stage_name, str):
            raise AnalysisPipelineReliabilityError(
                "Issue stage_name must be a string."
            )


@dataclass(frozen=True)
class StageReliabilityMetric:
    stage_name: str
    execution_count: int
    completed_count: int
    failed_count: int
    skipped_count: int
    pending_count: int
    running_count: int
    success_rate: float
    average_duration_seconds: float | None
    maximum_duration_seconds: float | None
    retry_count: int

    def __post_init__(self) -> None:
        if not isinstance(self.stage_name, str) or not self.stage_name.strip():
            raise AnalysisPipelineReliabilityError(
                "Metric stage_name must be a non-empty string."
            )

        for field_name in (
            "execution_count",
            "completed_count",
            "failed_count",
            "skipped_count",
            "pending_count",
            "running_count",
            "retry_count",
        ):
            value = getattr(self, field_name)
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise AnalysisPipelineReliabilityError(
                    f"{field_name} must be a non-negative integer."
                )

        if not isinstance(self.success_rate, (int, float)) or not (
            0.0 <= self.success_rate <= 1.0
        ):
            raise AnalysisPipelineReliabilityError(
                "success_rate must be between 0 and 1."
            )

        for field_name in (
            "average_duration_seconds",
            "maximum_duration_seconds",
        ):
            value = getattr(self, field_name)
            if value is not None and (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or value < 0
            ):
                raise AnalysisPipelineReliabilityError(
                    f"{field_name} must be a non-negative number or None."
                )


@dataclass(frozen=True)
class AnalysisPipelineReliabilityReport:
    total_pipelines: int
    successful_pipelines: int
    failed_pipelines: int
    incomplete_pipelines: int
    total_stage_executions: int
    completed_stage_executions: int
    failed_stage_executions: int
    skipped_stage_executions: int
    retry_count: int
    pipeline_success_rate: float
    stage_success_rate: float
    average_stage_duration_seconds: float | None
    stage_metrics: tuple[StageReliabilityMetric, ...]
    issues: tuple[PipelineReliabilityIssue, ...]

    def __post_init__(self) -> None:
        count_fields = (
            "total_pipelines",
            "successful_pipelines",
            "failed_pipelines",
            "incomplete_pipelines",
            "total_stage_executions",
            "completed_stage_executions",
            "failed_stage_executions",
            "skipped_stage_executions",
            "retry_count",
        )

        for field_name in count_fields:
            value = getattr(self, field_name)
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise AnalysisPipelineReliabilityError(
                    f"{field_name} must be a non-negative integer."
                )

        if (
            self.successful_pipelines
            + self.failed_pipelines
            + self.incomplete_pipelines
            != self.total_pipelines
        ):
            raise AnalysisPipelineReliabilityError(
                "Pipeline outcome counts must equal total_pipelines."
            )

        if not isinstance(self.stage_metrics, tuple) or not all(
            isinstance(metric, StageReliabilityMetric)
            for metric in self.stage_metrics
        ):
            raise AnalysisPipelineReliabilityError(
                "stage_metrics must be a tuple of StageReliabilityMetric objects."
            )

        if not isinstance(self.issues, tuple) or not all(
            isinstance(issue, PipelineReliabilityIssue)
            for issue in self.issues
        ):
            raise AnalysisPipelineReliabilityError(
                "issues must be a tuple of PipelineReliabilityIssue objects."
            )

        for field_name in ("pipeline_success_rate", "stage_success_rate"):
            value = getattr(self, field_name)
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not 0.0 <= value <= 1.0
            ):
                raise AnalysisPipelineReliabilityError(
                    f"{field_name} must be between 0 and 1."
                )

        if self.average_stage_duration_seconds is not None and (
            isinstance(self.average_stage_duration_seconds, bool)
            or not isinstance(self.average_stage_duration_seconds, (int, float))
            or self.average_stage_duration_seconds < 0
        ):
            raise AnalysisPipelineReliabilityError(
                "average_stage_duration_seconds must be non-negative or None."
            )

    @property
    def has_issues(self) -> bool:
        return bool(self.issues)

    @property
    def error_count(self) -> int:
        return sum(
            issue.severity is ReliabilitySeverity.ERROR for issue in self.issues
        )

    @property
    def warning_count(self) -> int:
        return sum(
            issue.severity is ReliabilitySeverity.WARNING for issue in self.issues
        )

    @property
    def info_count(self) -> int:
        return sum(
            issue.severity is ReliabilitySeverity.INFO for issue in self.issues
        )

    @property
    def is_reliable(self) -> bool:
        return self.failed_pipelines == 0 and self.error_count == 0

    def get_stage_metric(self, stage_name: str) -> StageReliabilityMetric | None:
        if not isinstance(stage_name, str) or not stage_name.strip():
            raise AnalysisPipelineReliabilityError(
                "stage_name must be a non-empty string."
            )

        normalized_name = stage_name.strip()
        return next(
            (
                metric
                for metric in self.stage_metrics
                if metric.stage_name == normalized_name
            ),
            None,
        )


class AnalysisPipelineReliabilityMonitoringService:
    """
    Monitors pipeline execution outcomes, stage reliability, retries and durations.

    A pipeline is:
    - successful when all expected stages are completed and no stage failed,
    - failed when at least one stage failed,
    - incomplete otherwise.

    Stage success rate is completed executions divided by all recorded
    stage executions. Pending, running and skipped stages are not successful.
    """

    def __init__(
        self,
        slow_stage_threshold_seconds: float | None = None,
        retry_warning_threshold: int = 2,
    ) -> None:
        if slow_stage_threshold_seconds is not None and (
            isinstance(slow_stage_threshold_seconds, bool)
            or not isinstance(slow_stage_threshold_seconds, (int, float))
            or slow_stage_threshold_seconds < 0
        ):
            raise AnalysisPipelineReliabilityError(
                "slow_stage_threshold_seconds must be non-negative or None."
            )

        if (
            isinstance(retry_warning_threshold, bool)
            or not isinstance(retry_warning_threshold, int)
            or retry_warning_threshold < 1
        ):
            raise AnalysisPipelineReliabilityError(
                "retry_warning_threshold must be a positive integer."
            )

        self._slow_stage_threshold_seconds = slow_stage_threshold_seconds
        self._retry_warning_threshold = retry_warning_threshold

    def monitor(
        self,
        executions: Iterable[PipelineExecution],
    ) -> AnalysisPipelineReliabilityReport:
        if isinstance(executions, (str, bytes, dict)):
            raise AnalysisPipelineReliabilityError(
                "executions must be an iterable of PipelineExecution objects."
            )

        try:
            pipeline_executions = tuple(executions)
        except TypeError as exc:
            raise AnalysisPipelineReliabilityError(
                "executions must be iterable."
            ) from exc

        if not all(
            isinstance(execution, PipelineExecution)
            for execution in pipeline_executions
        ):
            raise AnalysisPipelineReliabilityError(
                "Every execution must be a PipelineExecution object."
            )

        pipeline_ids = [execution.pipeline_id for execution in pipeline_executions]
        if len(pipeline_ids) != len(set(pipeline_ids)):
            raise AnalysisPipelineReliabilityError(
                "Pipeline execution IDs must be unique."
            )

        issues: list[PipelineReliabilityIssue] = []
        stage_records: dict[str, list[PipelineStageExecution]] = {}
        successful_pipelines = 0
        failed_pipelines = 0
        incomplete_pipelines = 0
        total_stage_executions = 0
        completed_stage_executions = 0
        failed_stage_executions = 0
        skipped_stage_executions = 0
        retry_count = 0
        all_durations: list[float] = []

        for execution in pipeline_executions:
            stage_names = [stage.stage_name for stage in execution.stages]

            for stage in execution.stages:
                total_stage_executions += 1
                stage_records.setdefault(stage.stage_name, []).append(stage)

                if stage.status is PipelineStageStatus.COMPLETED:
                    completed_stage_executions += 1
                elif stage.status is PipelineStageStatus.FAILED:
                    failed_stage_executions += 1
                    issues.append(
                        PipelineReliabilityIssue(
                            code="STAGE_FAILED",
                            severity=ReliabilitySeverity.ERROR,
                            pipeline_id=execution.pipeline_id,
                            stage_name=stage.stage_name,
                            message=(
                                f"Stage '{stage.stage_name}' failed: "
                                f"{stage.error_message.strip()}"
                            ),
                        )
                    )
                elif stage.status is PipelineStageStatus.SKIPPED:
                    skipped_stage_executions += 1
                    issues.append(
                        PipelineReliabilityIssue(
                            code="STAGE_SKIPPED",
                            severity=ReliabilitySeverity.WARNING,
                            pipeline_id=execution.pipeline_id,
                            stage_name=stage.stage_name,
                            message=f"Stage '{stage.stage_name}' was skipped.",
                        )
                    )
                elif stage.status is PipelineStageStatus.PENDING:
                    issues.append(
                        PipelineReliabilityIssue(
                            code="STAGE_PENDING",
                            severity=ReliabilitySeverity.WARNING,
                            pipeline_id=execution.pipeline_id,
                            stage_name=stage.stage_name,
                            message=f"Stage '{stage.stage_name}' is still pending.",
                        )
                    )
                elif stage.status is PipelineStageStatus.RUNNING:
                    issues.append(
                        PipelineReliabilityIssue(
                            code="STAGE_RUNNING",
                            severity=ReliabilitySeverity.INFO,
                            pipeline_id=execution.pipeline_id,
                            stage_name=stage.stage_name,
                            message=f"Stage '{stage.stage_name}' is still running.",
                        )
                    )

                if stage.attempt > 1:
                    retry_count += stage.attempt - 1
                    if stage.attempt >= self._retry_warning_threshold:
                        issues.append(
                            PipelineReliabilityIssue(
                                code="HIGH_RETRY_COUNT",
                                severity=ReliabilitySeverity.WARNING,
                                pipeline_id=execution.pipeline_id,
                                stage_name=stage.stage_name,
                                message=(
                                    f"Stage '{stage.stage_name}' required "
                                    f"{stage.attempt} attempts."
                                ),
                            )
                        )

                if stage.duration_seconds is not None:
                    all_durations.append(float(stage.duration_seconds))
                    if (
                        self._slow_stage_threshold_seconds is not None
                        and stage.duration_seconds
                        > self._slow_stage_threshold_seconds
                    ):
                        issues.append(
                            PipelineReliabilityIssue(
                                code="SLOW_STAGE",
                                severity=ReliabilitySeverity.WARNING,
                                pipeline_id=execution.pipeline_id,
                                stage_name=stage.stage_name,
                                message=(
                                    f"Stage '{stage.stage_name}' took "
                                    f"{stage.duration_seconds} seconds, exceeding "
                                    f"the configured threshold of "
                                    f"{self._slow_stage_threshold_seconds} seconds."
                                ),
                            )
                        )

            duplicate_stage_names = {
                name for name in stage_names if stage_names.count(name) > 1
            }
            for stage_name in sorted(duplicate_stage_names):
                issues.append(
                    PipelineReliabilityIssue(
                        code="DUPLICATE_STAGE_EXECUTION",
                        severity=ReliabilitySeverity.ERROR,
                        pipeline_id=execution.pipeline_id,
                        stage_name=stage_name,
                        message=(
                            f"Stage '{stage_name}' appears more than once "
                            "in the same pipeline execution."
                        ),
                    )
                )

            missing_stages = set(execution.expected_stages) - set(stage_names)
            for stage_name in sorted(missing_stages):
                issues.append(
                    PipelineReliabilityIssue(
                        code="MISSING_EXPECTED_STAGE",
                        severity=ReliabilitySeverity.ERROR,
                        pipeline_id=execution.pipeline_id,
                        stage_name=stage_name,
                        message=(
                            f"Expected stage '{stage_name}' was not recorded."
                        ),
                    )
                )

            has_failed_stage = any(
                stage.status is PipelineStageStatus.FAILED
                for stage in execution.stages
            )
            has_missing_stage = bool(missing_stages)
            all_expected_completed = all(
                any(
                    stage.stage_name == expected_name
                    and stage.status is PipelineStageStatus.COMPLETED
                    for stage in execution.stages
                )
                for expected_name in execution.expected_stages
            )

            if has_failed_stage:
                failed_pipelines += 1
            elif has_missing_stage or not all_expected_completed:
                incomplete_pipelines += 1
            else:
                successful_pipelines += 1

        stage_metrics = tuple(
            self._build_stage_metric(stage_name, records)
            for stage_name, records in sorted(stage_records.items())
        )

        pipeline_count = len(pipeline_executions)
        pipeline_success_rate = (
            successful_pipelines / pipeline_count if pipeline_count else 0.0
        )
        stage_success_rate = (
            completed_stage_executions / total_stage_executions
            if total_stage_executions
            else 0.0
        )

        return AnalysisPipelineReliabilityReport(
            total_pipelines=pipeline_count,
            successful_pipelines=successful_pipelines,
            failed_pipelines=failed_pipelines,
            incomplete_pipelines=incomplete_pipelines,
            total_stage_executions=total_stage_executions,
            completed_stage_executions=completed_stage_executions,
            failed_stage_executions=failed_stage_executions,
            skipped_stage_executions=skipped_stage_executions,
            retry_count=retry_count,
            pipeline_success_rate=pipeline_success_rate,
            stage_success_rate=stage_success_rate,
            average_stage_duration_seconds=(
                mean(all_durations) if all_durations else None
            ),
            stage_metrics=stage_metrics,
            issues=tuple(issues),
        )

    @staticmethod
    def _build_stage_metric(
        stage_name: str,
        records: list[PipelineStageExecution],
    ) -> StageReliabilityMetric:
        completed = sum(
            record.status is PipelineStageStatus.COMPLETED for record in records
        )
        failed = sum(
            record.status is PipelineStageStatus.FAILED for record in records
        )
        skipped = sum(
            record.status is PipelineStageStatus.SKIPPED for record in records
        )
        pending = sum(
            record.status is PipelineStageStatus.PENDING for record in records
        )
        running = sum(
            record.status is PipelineStageStatus.RUNNING for record in records
        )
        durations = [
            float(record.duration_seconds)
            for record in records
            if record.duration_seconds is not None
        ]
        total = len(records)

        return StageReliabilityMetric(
            stage_name=stage_name,
            execution_count=total,
            completed_count=completed,
            failed_count=failed,
            skipped_count=skipped,
            pending_count=pending,
            running_count=running,
            success_rate=completed / total if total else 0.0,
            average_duration_seconds=mean(durations) if durations else None,
            maximum_duration_seconds=max(durations) if durations else None,
            retry_count=sum(max(record.attempt - 1, 0) for record in records),
        )