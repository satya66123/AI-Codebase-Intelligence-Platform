import pytest

from app.application.performance_optimization_recommendation_service import (
    ComponentPerformanceSummary,
    OptimizationCategory,
    PerformanceMeasurement,
    PerformanceOptimizationError,
    PerformanceOptimizationRecommendationService,
    PerformanceOptimizationReport,
    PerformanceRecommendation,
    PerformanceSeverity,
)


class TestPerformanceOptimizationRecommendationService:
    def setup_method(self):
        self.service = PerformanceOptimizationRecommendationService()

    def test_empty_measurements_return_empty_report(self):
        result = self.service.analyze([])

        assert result.total_measurements == 0
        assert result.components_analyzed == 0
        assert result.total_duration_seconds == 0
        assert result.average_measurement_duration_seconds is None
        assert result.recommendations == ()
        assert result.component_summaries == ()

    def test_fast_measurement_has_no_recommendation(self):
        result = self.service.analyze(
            [PerformanceMeasurement("repository_scanner", 0.5)]
        )

        assert result.recommendation_count == 0
        assert result.has_recommendations is False

    def test_slow_execution_generates_recommendation(self):
        result = self.service.analyze(
            [PerformanceMeasurement("repository_scanner", 2.0)]
        )

        assert result.recommendation_count == 1
        recommendation = result.recommendations[0]
        assert recommendation.category is OptimizationCategory.EXECUTION_TIME
        assert recommendation.severity is PerformanceSeverity.MEDIUM

    def test_high_execution_time_generates_high_severity(self):
        result = self.service.analyze(
            [PerformanceMeasurement("code_analysis", 6.0)]
        )

        assert result.recommendations[0].severity is PerformanceSeverity.HIGH

    def test_critical_execution_time_generates_critical_severity(self):
        result = self.service.analyze(
            [PerformanceMeasurement("code_analysis", 16.0)]
        )

        assert result.recommendations[0].severity is PerformanceSeverity.CRITICAL

    def test_duration_equal_to_slow_threshold_does_not_trigger(self):
        service = PerformanceOptimizationRecommendationService(
            slow_duration_threshold_seconds=1.0
        )

        result = service.analyze(
            [PerformanceMeasurement("component", 1.0)]
        )

        assert result.recommendation_count == 0

    def test_duration_above_slow_threshold_triggers_recommendation(self):
        service = PerformanceOptimizationRecommendationService(
            slow_duration_threshold_seconds=1.0
        )

        result = service.analyze(
            [PerformanceMeasurement("component", 1.01)]
        )

        assert result.recommendation_count == 1

    def test_high_memory_usage_generates_recommendation(self):
        result = self.service.analyze(
            [PerformanceMeasurement("index_builder", 0.5, memory_mb=300)]
        )

        memory_recommendations = [
            item
            for item in result.recommendations
            if item.category is OptimizationCategory.MEMORY_USAGE
        ]

        assert len(memory_recommendations) == 1
        assert memory_recommendations[0].severity is PerformanceSeverity.HIGH

    def test_critical_memory_usage_generates_critical_recommendation(self):
        result = self.service.analyze(
            [PerformanceMeasurement("index_builder", 0.5, memory_mb=1200)]
        )

        memory_recommendations = [
            item
            for item in result.recommendations
            if item.category is OptimizationCategory.MEMORY_USAGE
        ]

        assert memory_recommendations[0].severity is PerformanceSeverity.CRITICAL

    def test_memory_equal_to_threshold_does_not_trigger(self):
        service = PerformanceOptimizationRecommendationService(
            high_memory_threshold_mb=256
        )

        result = service.analyze(
            [PerformanceMeasurement("component", 0.5, memory_mb=256)]
        )

        assert not any(
            item.category is OptimizationCategory.MEMORY_USAGE
            for item in result.recommendations
        )

    def test_high_invocation_count_generates_recommendation(self):
        result = self.service.analyze(
            [
                PerformanceMeasurement(
                    "retrieval_service",
                    0.2,
                    invocation_count=1500,
                )
            ]
        )

        assert any(
            item.category is OptimizationCategory.HIGH_INVOCATION_COUNT
            for item in result.recommendations
        )

    def test_invocation_count_equal_to_threshold_does_not_trigger(self):
        service = PerformanceOptimizationRecommendationService(
            high_invocation_threshold=100
        )

        result = service.analyze(
            [
                PerformanceMeasurement(
                    "retrieval_service",
                    0.2,
                    invocation_count=100,
                )
            ]
        )

        assert not any(
            item.category is OptimizationCategory.HIGH_INVOCATION_COUNT
            for item in result.recommendations
        )

    def test_low_cache_hit_rate_generates_recommendation(self):
        result = self.service.analyze(
            [
                PerformanceMeasurement(
                    "retrieval_service",
                    0.2,
                    invocation_count=100,
                    cache_hits=20,
                    cache_misses=80,
                )
            ]
        )

        assert any(
            item.category is OptimizationCategory.CACHE_EFFICIENCY
            for item in result.recommendations
        )

    def test_high_cache_hit_rate_does_not_generate_recommendation(self):
        result = self.service.analyze(
            [
                PerformanceMeasurement(
                    "retrieval_service",
                    0.2,
                    invocation_count=100,
                    cache_hits=90,
                    cache_misses=10,
                )
            ]
        )

        assert not any(
            item.category is OptimizationCategory.CACHE_EFFICIENCY
            for item in result.recommendations
        )

    def test_cache_hit_rate_equal_to_threshold_does_not_trigger(self):
        service = PerformanceOptimizationRecommendationService(
            low_cache_hit_rate_threshold=0.5
        )

        result = service.analyze(
            [
                PerformanceMeasurement(
                    "retrieval_service",
                    0.2,
                    invocation_count=100,
                    cache_hits=50,
                    cache_misses=50,
                )
            ]
        )

        assert not any(
            item.category is OptimizationCategory.CACHE_EFFICIENCY
            for item in result.recommendations
        )

    def test_no_cache_activity_does_not_generate_cache_recommendation(self):
        result = self.service.analyze(
            [PerformanceMeasurement("retrieval_service", 0.2)]
        )

        assert not any(
            item.category is OptimizationCategory.CACHE_EFFICIENCY
            for item in result.recommendations
        )

    def test_baseline_regression_generates_recommendation(self):
        result = self.service.analyze(
            [
                PerformanceMeasurement(
                    "analysis_service",
                    duration_seconds=2.0,
                    baseline_duration_seconds=1.0,
                )
            ]
        )

        assert any(
            item.category is OptimizationCategory.BASELINE_REGRESSION
            for item in result.recommendations
        )

    def test_baseline_regression_generates_high_severity_for_double_duration(self):
        result = self.service.analyze(
            [
                PerformanceMeasurement(
                    "analysis_service",
                    duration_seconds=3.0,
                    baseline_duration_seconds=1.0,
                )
            ]
        )

        regression = next(
            item
            for item in result.recommendations
            if item.category is OptimizationCategory.BASELINE_REGRESSION
        )

        assert regression.severity is PerformanceSeverity.HIGH

    def test_baseline_regression_below_threshold_does_not_trigger(self):
        service = PerformanceOptimizationRecommendationService(
            baseline_regression_threshold=0.25
        )

        result = service.analyze(
            [
                PerformanceMeasurement(
                    "analysis_service",
                    duration_seconds=1.2,
                    baseline_duration_seconds=1.0,
                )
            ]
        )

        assert not any(
            item.category is OptimizationCategory.BASELINE_REGRESSION
            for item in result.recommendations
        )

    def test_zero_baseline_does_not_trigger_regression(self):
        result = self.service.analyze(
            [
                PerformanceMeasurement(
                    "analysis_service",
                    duration_seconds=2.0,
                    baseline_duration_seconds=0.0,
                )
            ]
        )

        assert not any(
            item.category is OptimizationCategory.BASELINE_REGRESSION
            for item in result.recommendations
        )

    def test_multiple_optimization_categories_can_be_reported(self):
        result = self.service.analyze(
            [
                PerformanceMeasurement(
                    "analysis_service",
                    duration_seconds=20.0,
                    memory_mb=1500,
                    invocation_count=2000,
                    cache_hits=10,
                    cache_misses=90,
                    baseline_duration_seconds=5.0,
                )
            ]
        )

        categories = {item.category for item in result.recommendations}

        assert OptimizationCategory.EXECUTION_TIME in categories
        assert OptimizationCategory.MEMORY_USAGE in categories
        assert OptimizationCategory.HIGH_INVOCATION_COUNT in categories
        assert OptimizationCategory.CACHE_EFFICIENCY in categories
        assert OptimizationCategory.BASELINE_REGRESSION in categories

    def test_recommendations_are_sorted_by_severity(self):
        result = self.service.analyze(
            [
                PerformanceMeasurement(
                    "medium_component",
                    duration_seconds=2.0,
                ),
                PerformanceMeasurement(
                    "critical_component",
                    duration_seconds=20.0,
                ),
            ]
        )

        severities = [item.severity for item in result.recommendations]

        ranks = {
            PerformanceSeverity.LOW: 1,
            PerformanceSeverity.MEDIUM: 2,
            PerformanceSeverity.HIGH: 3,
            PerformanceSeverity.CRITICAL: 4,
        }

        assert ranks[severities[0]] >= ranks[severities[-1]]

    def test_component_summaries_are_sorted_by_name(self):
        result = self.service.analyze(
            [
                PerformanceMeasurement("z_service", 0.5),
                PerformanceMeasurement("a_service", 0.6),
                PerformanceMeasurement("m_service", 0.7),
            ]
        )

        assert [
            item.component_name for item in result.component_summaries
        ] == ["a_service", "m_service", "z_service"]

    def test_measurements_for_same_component_are_aggregated(self):
        result = self.service.analyze(
            [
                PerformanceMeasurement("analysis_service", 1.0),
                PerformanceMeasurement("analysis_service", 3.0),
            ]
        )

        summary = result.get_component_summary("analysis_service")

        assert summary.measurement_count == 2
        assert summary.total_duration_seconds == 4.0
        assert summary.average_duration_seconds == 2.0
        assert summary.maximum_duration_seconds == 3.0

    def test_total_duration_is_calculated(self):
        result = self.service.analyze(
            [
                PerformanceMeasurement("service_a", 1.0),
                PerformanceMeasurement("service_b", 2.0),
                PerformanceMeasurement("service_c", 3.0),
            ]
        )

        assert result.total_duration_seconds == 6.0
        assert result.average_measurement_duration_seconds == 2.0

    def test_memory_summary_ignores_missing_memory_values(self):
        result = self.service.analyze(
            [
                PerformanceMeasurement("analysis_service", 1.0, memory_mb=100),
                PerformanceMeasurement("analysis_service", 2.0),
            ]
        )

        summary = result.get_component_summary("analysis_service")

        assert summary.average_memory_mb == 100.0
        assert summary.maximum_memory_mb == 100.0

    def test_memory_summary_is_none_without_memory_measurements(self):
        result = self.service.analyze(
            [PerformanceMeasurement("analysis_service", 1.0)]
        )

        summary = result.get_component_summary("analysis_service")

        assert summary.average_memory_mb is None
        assert summary.maximum_memory_mb is None

    def test_cache_hit_rate_is_aggregated_across_measurements(self):
        result = self.service.analyze(
            [
                PerformanceMeasurement(
                    "retrieval_service",
                    1.0,
                    invocation_count=10,
                    cache_hits=8,
                    cache_misses=2,
                ),
                PerformanceMeasurement(
                    "retrieval_service",
                    1.0,
                    invocation_count=10,
                    cache_hits=2,
                    cache_misses=8,
                ),
            ]
        )

        summary = result.get_component_summary("retrieval_service")

        assert summary.cache_hit_rate == pytest.approx(0.5)

    def test_cache_hit_rate_is_none_without_cache_activity(self):
        result = self.service.analyze(
            [PerformanceMeasurement("retrieval_service", 1.0)]
        )

        summary = result.get_component_summary("retrieval_service")

        assert summary.cache_hit_rate is None

    def test_total_invocations_are_aggregated(self):
        result = self.service.analyze(
            [
                PerformanceMeasurement(
                    "analysis_service",
                    1.0,
                    invocation_count=10,
                ),
                PerformanceMeasurement(
                    "analysis_service",
                    1.0,
                    invocation_count=20,
                ),
            ]
        )

        summary = result.get_component_summary("analysis_service")

        assert summary.total_invocations == 30

    def test_get_component_summary_returns_none_for_unknown_component(self):
        result = self.service.analyze([])

        assert result.get_component_summary("unknown") is None

    def test_get_component_summary_rejects_empty_name(self):
        result = self.service.analyze([])

        with pytest.raises(PerformanceOptimizationError):
            result.get_component_summary(" ")

    def test_recommendations_can_be_filtered_by_severity(self):
        result = self.service.analyze(
            [
                PerformanceMeasurement("medium_service", 2.0),
                PerformanceMeasurement("critical_service", 20.0),
            ]
        )

        critical = result.recommendations_by_severity(
            PerformanceSeverity.CRITICAL
        )

        assert len(critical) == 1
        assert critical[0].component_name == "critical_service"

    def test_recommendations_by_severity_rejects_invalid_value(self):
        result = self.service.analyze([])

        with pytest.raises(PerformanceOptimizationError):
            result.recommendations_by_severity("critical")

    def test_critical_recommendation_count(self):
        result = self.service.analyze(
            [PerformanceMeasurement("critical_service", 20.0)]
        )

        assert result.critical_recommendation_count == 1

    def test_high_priority_count_includes_critical_and_high(self):
        result = self.service.analyze(
            [
                PerformanceMeasurement("high_service", 6.0),
                PerformanceMeasurement("critical_service", 20.0),
            ]
        )

        assert result.high_priority_recommendation_count == 2

    def test_non_iterable_measurements_are_rejected(self):
        with pytest.raises(PerformanceOptimizationError):
            self.service.analyze(123)

    def test_string_measurements_are_rejected(self):
        with pytest.raises(PerformanceOptimizationError):
            self.service.analyze("invalid")

    def test_mapping_measurements_are_rejected(self):
        with pytest.raises(PerformanceOptimizationError):
            self.service.analyze({"component": 1.0})

    def test_invalid_measurement_object_is_rejected(self):
        with pytest.raises(PerformanceOptimizationError):
            self.service.analyze([{"component_name": "service"}])

    def test_measurement_rejects_empty_component_name(self):
        with pytest.raises(PerformanceOptimizationError):
            PerformanceMeasurement(" ", 1.0)

    def test_measurement_rejects_negative_duration(self):
        with pytest.raises(PerformanceOptimizationError):
            PerformanceMeasurement("service", -1.0)

    def test_measurement_rejects_boolean_duration(self):
        with pytest.raises(PerformanceOptimizationError):
            PerformanceMeasurement("service", True)

    def test_measurement_rejects_negative_memory(self):
        with pytest.raises(PerformanceOptimizationError):
            PerformanceMeasurement("service", 1.0, memory_mb=-1)

    def test_measurement_rejects_negative_invocation_count(self):
        with pytest.raises(PerformanceOptimizationError):
            PerformanceMeasurement("service", 1.0, invocation_count=-1)

    def test_measurement_rejects_boolean_invocation_count(self):
        with pytest.raises(PerformanceOptimizationError):
            PerformanceMeasurement("service", 1.0, invocation_count=True)

    def test_measurement_rejects_negative_cache_hits(self):
        with pytest.raises(PerformanceOptimizationError):
            PerformanceMeasurement("service", 1.0, cache_hits=-1)

    def test_measurement_rejects_cache_counts_above_invocations(self):
        with pytest.raises(PerformanceOptimizationError):
            PerformanceMeasurement(
                "service",
                1.0,
                invocation_count=5,
                cache_hits=4,
                cache_misses=2,
            )

    def test_measurement_rejects_negative_baseline(self):
        with pytest.raises(PerformanceOptimizationError):
            PerformanceMeasurement(
                "service",
                1.0,
                baseline_duration_seconds=-1,
            )

    def test_invalid_duration_threshold_order_is_rejected(self):
        with pytest.raises(PerformanceOptimizationError):
            PerformanceOptimizationRecommendationService(
                slow_duration_threshold_seconds=5,
                high_duration_threshold_seconds=2,
            )

    def test_invalid_critical_duration_threshold_order_is_rejected(self):
        with pytest.raises(PerformanceOptimizationError):
            PerformanceOptimizationRecommendationService(
                slow_duration_threshold_seconds=1,
                high_duration_threshold_seconds=5,
                critical_duration_threshold_seconds=2,
            )

    def test_invalid_memory_threshold_order_is_rejected(self):
        with pytest.raises(PerformanceOptimizationError):
            PerformanceOptimizationRecommendationService(
                high_memory_threshold_mb=500,
                critical_memory_threshold_mb=200,
            )

    def test_invalid_invocation_threshold_is_rejected(self):
        with pytest.raises(PerformanceOptimizationError):
            PerformanceOptimizationRecommendationService(
                high_invocation_threshold=0
            )

    def test_invalid_cache_threshold_is_rejected(self):
        with pytest.raises(PerformanceOptimizationError):
            PerformanceOptimizationRecommendationService(
                low_cache_hit_rate_threshold=1.5
            )

    def test_negative_baseline_regression_threshold_is_rejected(self):
        with pytest.raises(PerformanceOptimizationError):
            PerformanceOptimizationRecommendationService(
                baseline_regression_threshold=-0.1
            )

    def test_boolean_threshold_is_rejected(self):
        with pytest.raises(PerformanceOptimizationError):
            PerformanceOptimizationRecommendationService(
                slow_duration_threshold_seconds=True
            )

    def test_recommendation_model_rejects_invalid_category(self):
        with pytest.raises(PerformanceOptimizationError):
            PerformanceRecommendation(
                component_name="service",
                category="execution_time",
                severity=PerformanceSeverity.HIGH,
                title="Optimize",
                description="Slow execution.",
                suggested_action="Profile the service.",
                measured_value=2.0,
            )

    def test_recommendation_model_rejects_invalid_severity(self):
        with pytest.raises(PerformanceOptimizationError):
            PerformanceRecommendation(
                component_name="service",
                category=OptimizationCategory.EXECUTION_TIME,
                severity="high",
                title="Optimize",
                description="Slow execution.",
                suggested_action="Profile the service.",
                measured_value=2.0,
            )

    def test_recommendation_model_rejects_negative_measured_value(self):
        with pytest.raises(PerformanceOptimizationError):
            PerformanceRecommendation(
                component_name="service",
                category=OptimizationCategory.EXECUTION_TIME,
                severity=PerformanceSeverity.HIGH,
                title="Optimize",
                description="Slow execution.",
                suggested_action="Profile the service.",
                measured_value=-1,
            )

    def test_component_summary_rejects_cache_rate_above_one(self):
        with pytest.raises(PerformanceOptimizationError):
            ComponentPerformanceSummary(
                component_name="service",
                measurement_count=1,
                total_duration_seconds=1.0,
                average_duration_seconds=1.0,
                maximum_duration_seconds=1.0,
                total_invocations=1,
                average_memory_mb=None,
                maximum_memory_mb=None,
                cache_hit_rate=1.5,
            )

    def test_report_rejects_inconsistent_component_count(self):
        with pytest.raises(PerformanceOptimizationError):
            PerformanceOptimizationReport(
                total_measurements=1,
                components_analyzed=1,
                total_duration_seconds=1.0,
                average_measurement_duration_seconds=1.0,
                recommendations=(),
                component_summaries=(),
            )

    def test_report_rejects_invalid_recommendation_collection(self):
        with pytest.raises(PerformanceOptimizationError):
            PerformanceOptimizationReport(
                total_measurements=0,
                components_analyzed=0,
                total_duration_seconds=0.0,
                average_measurement_duration_seconds=None,
                recommendations=[],
                component_summaries=(),
            )