import pytest

from appy.application.analysis_pipeline_reliability_monitoring_service import (
    AnalysisPipelineReliabilityError,
    AnalysisPipelineReliabilityMonitoringService,
    AnalysisPipelineReliabilityReport,
    PipelineExecution,
    PipelineStageExecution,
    PipelineStageStatus,
    ReliabilitySeverity,
    StageReliabilityMetric,
)


def stage(
    name,
    status=PipelineStageStatus.COMPLETED,
    duration=None,
    attempt=1,
    error="",
):
    return PipelineStageExecution(
        stage_name=name,
        status=status,
        duration_seconds=duration,
        attempt=attempt,
        error_message=error,
    )


def execution(
    pipeline_id="pipeline-1",
    stages=(),
    expected=("discovery", "analysis", "report"),
):
    return PipelineExecution(
        pipeline_id=pipeline_id,
        stages=tuple(stages),
        expected_stages=tuple(expected),
    )


class TestAnalysisPipelineReliabilityMonitoringService:
    def setup_method(self):
        self.service = AnalysisPipelineReliabilityMonitoringService()

    def test_successful_pipeline_report(self):
        result = self.service.monitor(
            [
                execution(
                    stages=[
                        stage("discovery", duration=1.0),
                        stage("analysis", duration=2.0),
                        stage("report", duration=3.0),
                    ]
                )
            ]
        )

        assert result.total_pipelines == 1
        assert result.successful_pipelines == 1
        assert result.failed_pipelines == 0
        assert result.incomplete_pipelines == 0
        assert result.pipeline_success_rate == 1.0
        assert result.is_reliable is True

    def test_empty_execution_collection_returns_empty_report(self):
        result = self.service.monitor([])

        assert result.total_pipelines == 0
        assert result.total_stage_executions == 0
        assert result.pipeline_success_rate == 0.0
        assert result.stage_success_rate == 0.0
        assert result.average_stage_duration_seconds is None
        assert result.stage_metrics == ()
        assert result.issues == ()

    def test_failed_pipeline_is_counted(self):
        result = self.service.monitor(
            [
                execution(
                    stages=[
                        stage("discovery"),
                        stage(
                            "analysis",
                            PipelineStageStatus.FAILED,
                            error="Analysis failed.",
                        ),
                    ]
                )
            ]
        )

        assert result.failed_pipelines == 1
        assert result.successful_pipelines == 0
        assert result.is_reliable is False
        assert result.error_count == 2
        assert result.issues[0].code == "STAGE_FAILED"

    def test_incomplete_pipeline_is_counted(self):
        result = self.service.monitor(
            [
                execution(
                    stages=[
                        stage("discovery"),
                        stage("analysis"),
                    ]
                )
            ]
        )

        assert result.incomplete_pipelines == 1
        assert result.successful_pipelines == 0
        assert result.failed_pipelines == 0

    def test_missing_expected_stage_is_reported(self):
        result = self.service.monitor(
            [
                execution(
                    stages=[stage("discovery"), stage("analysis")]
                )
            ]
        )

        missing = [
            issue
            for issue in result.issues
            if issue.code == "MISSING_EXPECTED_STAGE"
        ]

        assert len(missing) == 1
        assert missing[0].stage_name == "report"
        assert missing[0].severity is ReliabilitySeverity.ERROR

    def test_missing_expected_stage_makes_pipeline_incomplete(self):
        result = self.service.monitor(
            [
                execution(
                    stages=[stage("discovery"), stage("analysis")]
                )
            ]
        )

        assert result.incomplete_pipelines == 1
        assert result.failed_pipelines == 0

    def test_pending_stage_is_reported(self):
        result = self.service.monitor(
            [
                execution(
                    stages=[
                        stage("discovery"),
                        stage("analysis", PipelineStageStatus.PENDING),
                    ]
                )
            ]
        )

        assert any(issue.code == "STAGE_PENDING" for issue in result.issues)
        assert result.incomplete_pipelines == 1

    def test_running_stage_is_reported_as_information(self):
        result = self.service.monitor(
            [
                execution(
                    stages=[
                        stage("discovery"),
                        stage("analysis", PipelineStageStatus.RUNNING),
                    ]
                )
            ]
        )

        running_issues = [
            issue for issue in result.issues if issue.code == "STAGE_RUNNING"
        ]

        assert len(running_issues) == 1
        assert running_issues[0].severity is ReliabilitySeverity.INFO

    def test_skipped_stage_is_reported(self):
        result = self.service.monitor(
            [
                execution(
                    stages=[
                        stage("discovery"),
                        stage("analysis", PipelineStageStatus.SKIPPED),
                    ]
                )
            ]
        )

        assert result.skipped_stage_executions == 1
        assert any(issue.code == "STAGE_SKIPPED" for issue in result.issues)
        assert result.warning_count == 1

    def test_failed_stage_takes_precedence_over_incomplete_status(self):
        result = self.service.monitor(
            [
                execution(
                    stages=[
                        stage(
                            "discovery",
                            PipelineStageStatus.FAILED,
                            error="Discovery failed.",
                        )
                    ]
                )
            ]
        )

        assert result.failed_pipelines == 1
        assert result.incomplete_pipelines == 0

    def test_retry_count_is_aggregated(self):
        result = self.service.monitor(
            [
                execution(
                    stages=[
                        stage("discovery", attempt=3),
                        stage("analysis"),
                        stage("report"),
                    ]
                )
            ]
        )

        assert result.retry_count == 2

    def test_retry_warning_is_generated_at_threshold(self):
        service = AnalysisPipelineReliabilityMonitoringService(
            retry_warning_threshold=2
        )

        result = service.monitor(
            [
                execution(
                    stages=[
                        stage("discovery", attempt=2),
                        stage("analysis"),
                        stage("report"),
                    ]
                )
            ]
        )

        assert any(
            issue.code == "HIGH_RETRY_COUNT" for issue in result.issues
        )

    def test_retry_warning_is_not_generated_below_threshold(self):
        service = AnalysisPipelineReliabilityMonitoringService(
            retry_warning_threshold=3
        )

        result = service.monitor(
            [
                execution(
                    stages=[
                        stage("discovery", attempt=2),
                        stage("analysis"),
                        stage("report"),
                    ]
                )
            ]
        )

        assert not any(
            issue.code == "HIGH_RETRY_COUNT" for issue in result.issues
        )

    def test_slow_stage_is_reported(self):
        service = AnalysisPipelineReliabilityMonitoringService(
            slow_stage_threshold_seconds=2.0
        )

        result = service.monitor(
            [
                execution(
                    stages=[
                        stage("discovery", duration=1.0),
                        stage("analysis", duration=5.0),
                        stage("report", duration=1.0),
                    ]
                )
            ]
        )

        slow_issues = [
            issue for issue in result.issues if issue.code == "SLOW_STAGE"
        ]

        assert len(slow_issues) == 1
        assert slow_issues[0].stage_name == "analysis"

    def test_duration_equal_to_threshold_is_not_slow(self):
        service = AnalysisPipelineReliabilityMonitoringService(
            slow_stage_threshold_seconds=2.0
        )

        result = service.monitor(
            [
                execution(
                    stages=[
                        stage("discovery", duration=2.0),
                        stage("analysis", duration=1.0),
                        stage("report", duration=1.0),
                    ]
                )
            ]
        )

        assert not any(
            issue.code == "SLOW_STAGE" for issue in result.issues
        )

    def test_average_stage_duration_is_calculated(self):
        result = self.service.monitor(
            [
                execution(
                    stages=[
                        stage("discovery", duration=2.0),
                        stage("analysis", duration=4.0),
                        stage("report", duration=6.0),
                    ]
                )
            ]
        )

        assert result.average_stage_duration_seconds == 4.0

    def test_average_duration_ignores_missing_durations(self):
        result = self.service.monitor(
            [
                execution(
                    stages=[
                        stage("discovery", duration=2.0),
                        stage("analysis"),
                        stage("report", duration=4.0),
                    ]
                )
            ]
        )

        assert result.average_stage_duration_seconds == 3.0

    def test_average_duration_is_none_when_no_durations_exist(self):
        result = self.service.monitor(
            [
                execution(
                    stages=[
                        stage("discovery"),
                        stage("analysis"),
                        stage("report"),
                    ]
                )
            ]
        )

        assert result.average_stage_duration_seconds is None

    def test_stage_metrics_are_created(self):
        result = self.service.monitor(
            [
                execution(
                    stages=[
                        stage("discovery", duration=2.0),
                        stage("analysis", duration=4.0),
                        stage("report", duration=6.0),
                    ]
                )
            ]
        )

        assert len(result.stage_metrics) == 3
        assert [metric.stage_name for metric in result.stage_metrics] == [
            "analysis",
            "discovery",
            "report",
        ]

    def test_stage_metric_counts_completed_and_failed_executions(self):
        result = self.service.monitor(
            [
                execution(
                    pipeline_id="pipeline-1",
                    stages=[
                        stage("analysis"),
                        stage("discovery"),
                        stage("report"),
                    ],
                ),
                execution(
                    pipeline_id="pipeline-2",
                    stages=[
                        stage(
                            "analysis",
                            PipelineStageStatus.FAILED,
                            error="Analysis failed.",
                        ),
                        stage("discovery"),
                        stage("report"),
                    ],
                ),
            ]
        )

        metric = result.get_stage_metric("analysis")

        assert metric is not None
        assert metric.execution_count == 2
        assert metric.completed_count == 1
        assert metric.failed_count == 1
        assert metric.success_rate == 0.5

    def test_stage_metric_calculates_duration_statistics(self):
        result = self.service.monitor(
            [
                execution(
                    stages=[
                        stage("analysis", duration=2.0),
                        stage("discovery", duration=1.0),
                        stage("report", duration=1.0),
                    ]
                ),
                execution(
                    pipeline_id="pipeline-2",
                    stages=[
                        stage("analysis", duration=4.0),
                        stage("discovery", duration=1.0),
                        stage("report", duration=1.0),
                    ],
                ),
            ]
        )

        metric = result.get_stage_metric("analysis")

        assert metric.average_duration_seconds == 3.0
        assert metric.maximum_duration_seconds == 4.0

    def test_stage_metric_calculates_retry_count(self):
        result = self.service.monitor(
            [
                execution(
                    stages=[
                        stage("analysis", attempt=3),
                        stage("discovery"),
                        stage("report"),
                    ]
                )
            ]
        )

        metric = result.get_stage_metric("analysis")

        assert metric.retry_count == 2

    def test_stage_success_rate_uses_all_recorded_stage_executions(self):
        result = self.service.monitor(
            [
                execution(
                    stages=[
                        stage("discovery"),
                        stage("analysis", PipelineStageStatus.FAILED, error="Failed."),
                        stage("report", PipelineStageStatus.SKIPPED),
                    ]
                )
            ]
        )

        assert result.stage_success_rate == pytest.approx(1 / 3)

    def test_duplicate_stage_execution_is_reported(self):
        result = self.service.monitor(
            [
                execution(
                    stages=[
                        stage("discovery"),
                        stage("analysis"),
                        stage("analysis"),
                    ]
                )
            ]
        )

        duplicates = [
            issue
            for issue in result.issues
            if issue.code == "DUPLICATE_STAGE_EXECUTION"
        ]

        assert len(duplicates) == 1
        assert duplicates[0].stage_name == "analysis"

    def test_multiple_pipeline_outcomes_are_aggregated(self):
        result = self.service.monitor(
            [
                execution(
                    pipeline_id="success",
                    stages=[
                        stage("discovery"),
                        stage("analysis"),
                        stage("report"),
                    ],
                ),
                execution(
                    pipeline_id="failed",
                    stages=[
                        stage(
                            "discovery",
                            PipelineStageStatus.FAILED,
                            error="Failed.",
                        )
                    ],
                ),
                execution(
                    pipeline_id="incomplete",
                    stages=[stage("discovery")],
                ),
            ]
        )

        assert result.total_pipelines == 3
        assert result.successful_pipelines == 1
        assert result.failed_pipelines == 1
        assert result.incomplete_pipelines == 1
        assert result.pipeline_success_rate == pytest.approx(1 / 3)

    def test_get_stage_metric_returns_none_for_unknown_stage(self):
        result = self.service.monitor([])

        assert result.get_stage_metric("unknown") is None

    def test_get_stage_metric_rejects_empty_name(self):
        result = self.service.monitor([])

        with pytest.raises(AnalysisPipelineReliabilityError):
            result.get_stage_metric(" ")

    def test_report_exposes_issue_severity_counts(self):
        result = self.service.monitor(
            [
                execution(
                    stages=[
                        stage(
                            "discovery",
                            PipelineStageStatus.FAILED,
                            error="Failed.",
                        ),
                        stage("analysis", PipelineStageStatus.SKIPPED),
                        stage("report", PipelineStageStatus.RUNNING),
                    ]
                )
            ]
        )

        assert result.error_count == 1
        assert result.warning_count == 1
        assert result.info_count == 1
        assert result.has_issues is True

    def test_report_is_not_reliable_when_pipeline_failed(self):
        result = self.service.monitor(
            [
                execution(
                    stages=[
                        stage(
                            "discovery",
                            PipelineStageStatus.FAILED,
                            error="Failed.",
                        )
                    ]
                )
            ]
        )

        assert result.is_reliable is False

    def test_report_is_reliable_for_successful_pipeline(self):
        result = self.service.monitor(
            [
                execution(
                    stages=[
                        stage("discovery"),
                        stage("analysis"),
                        stage("report"),
                    ]
                )
            ]
        )

        assert result.is_reliable is True

    def test_duplicate_pipeline_ids_are_rejected(self):
        with pytest.raises(AnalysisPipelineReliabilityError):
            self.service.monitor(
                [
                    execution(pipeline_id="duplicate", stages=[]),
                    execution(pipeline_id="duplicate", stages=[]),
                ]
            )

    def test_non_pipeline_execution_is_rejected(self):
        with pytest.raises(AnalysisPipelineReliabilityError):
            self.service.monitor([{"pipeline_id": "pipeline-1"}])

    def test_non_iterable_executions_are_rejected(self):
        with pytest.raises(AnalysisPipelineReliabilityError):
            self.service.monitor(123)

    def test_string_executions_are_rejected(self):
        with pytest.raises(AnalysisPipelineReliabilityError):
            self.service.monitor("invalid")

    def test_invalid_slow_stage_threshold_is_rejected(self):
        with pytest.raises(AnalysisPipelineReliabilityError):
            AnalysisPipelineReliabilityMonitoringService(
                slow_stage_threshold_seconds=-1
            )

    def test_boolean_slow_stage_threshold_is_rejected(self):
        with pytest.raises(AnalysisPipelineReliabilityError):
            AnalysisPipelineReliabilityMonitoringService(
                slow_stage_threshold_seconds=True
            )

    def test_invalid_retry_threshold_is_rejected(self):
        with pytest.raises(AnalysisPipelineReliabilityError):
            AnalysisPipelineReliabilityMonitoringService(
                retry_warning_threshold=0
            )

    def test_boolean_retry_threshold_is_rejected(self):
        with pytest.raises(AnalysisPipelineReliabilityError):
            AnalysisPipelineReliabilityMonitoringService(
                retry_warning_threshold=True
            )

    def test_stage_rejects_empty_name(self):
        with pytest.raises(AnalysisPipelineReliabilityError):
            PipelineStageExecution(
                stage_name=" ",
                status=PipelineStageStatus.COMPLETED,
            )

    def test_stage_rejects_invalid_status(self):
        with pytest.raises(AnalysisPipelineReliabilityError):
            PipelineStageExecution(
                stage_name="analysis",
                status="completed",
            )

    def test_stage_rejects_negative_duration(self):
        with pytest.raises(AnalysisPipelineReliabilityError):
            PipelineStageExecution(
                stage_name="analysis",
                status=PipelineStageStatus.COMPLETED,
                duration_seconds=-1,
            )

    def test_stage_rejects_boolean_duration(self):
        with pytest.raises(AnalysisPipelineReliabilityError):
            PipelineStageExecution(
                stage_name="analysis",
                status=PipelineStageStatus.COMPLETED,
                duration_seconds=True,
            )

    def test_stage_rejects_invalid_attempt(self):
        with pytest.raises(AnalysisPipelineReliabilityError):
            PipelineStageExecution(
                stage_name="analysis",
                status=PipelineStageStatus.COMPLETED,
                attempt=0,
            )

    def test_failed_stage_requires_error_message(self):
        with pytest.raises(AnalysisPipelineReliabilityError):
            PipelineStageExecution(
                stage_name="analysis",
                status=PipelineStageStatus.FAILED,
            )

    def test_pipeline_execution_rejects_empty_id(self):
        with pytest.raises(AnalysisPipelineReliabilityError):
            PipelineExecution(pipeline_id=" ", stages=())

    def test_pipeline_execution_requires_stage_tuple(self):
        with pytest.raises(AnalysisPipelineReliabilityError):
            PipelineExecution(
                pipeline_id="pipeline-1",
                stages=[stage("analysis")],
            )

    def test_pipeline_execution_rejects_duplicate_expected_stages(self):
        with pytest.raises(AnalysisPipelineReliabilityError):
            PipelineExecution(
                pipeline_id="pipeline-1",
                stages=(),
                expected_stages=("analysis", "analysis"),
            )

    def test_stage_metric_rejects_negative_counts(self):
        with pytest.raises(AnalysisPipelineReliabilityError):
            StageReliabilityMetric(
                stage_name="analysis",
                execution_count=-1,
                completed_count=0,
                failed_count=0,
                skipped_count=0,
                pending_count=0,
                running_count=0,
                success_rate=0.0,
                average_duration_seconds=None,
                maximum_duration_seconds=None,
                retry_count=0,
            )

    def test_report_rejects_inconsistent_pipeline_counts(self):
        with pytest.raises(AnalysisPipelineReliabilityError):
            AnalysisPipelineReliabilityReport(
                total_pipelines=2,
                successful_pipelines=1,
                failed_pipelines=0,
                incomplete_pipelines=0,
                total_stage_executions=0,
                completed_stage_executions=0,
                failed_stage_executions=0,
                skipped_stage_executions=0,
                retry_count=0,
                pipeline_success_rate=0.5,
                stage_success_rate=0.0,
                average_stage_duration_seconds=None,
                stage_metrics=(),
                issues=(),
            )