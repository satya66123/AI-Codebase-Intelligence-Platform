from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from enum import Enum
from statistics import mean


class PerformanceOptimizationError(ValueError):
    """Raised when performance analysis receives invalid input."""


class PerformanceSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class OptimizationCategory(str, Enum):
    EXECUTION_TIME = "execution_time"
    MEMORY_USAGE = "memory_usage"
    HIGH_INVOCATION_COUNT = "high_invocation_count"
    CACHE_EFFICIENCY = "cache_efficiency"
    BASELINE_REGRESSION = "baseline_regression"


@dataclass(frozen=True)
class PerformanceMeasurement:
    component_name: str
    duration_seconds: float
    memory_mb: float | None = None
    invocation_count: int = 1
    cache_hits: int = 0
    cache_misses: int = 0
    baseline_duration_seconds: float | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.component_name, str) or not self.component_name.strip():
            raise PerformanceOptimizationError(
                "component_name must be a non-empty string."
            )

        for field_name in (
            "duration_seconds",
            "memory_mb",
            "baseline_duration_seconds",
        ):
            value = getattr(self, field_name)
            if value is None and field_name == "memory_mb":
                continue
            if value is None and field_name == "baseline_duration_seconds":
                continue
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or value < 0
            ):
                raise PerformanceOptimizationError(
                    f"{field_name} must be a non-negative number."
                )

        for field_name in ("invocation_count", "cache_hits", "cache_misses"):
            value = getattr(self, field_name)
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise PerformanceOptimizationError(
                    f"{field_name} must be a non-negative integer."
                )

        if self.cache_hits + self.cache_misses > self.invocation_count:
            raise PerformanceOptimizationError(
                "cache_hits plus cache_misses cannot exceed invocation_count."
            )


@dataclass(frozen=True)
class PerformanceRecommendation:
    component_name: str
    category: OptimizationCategory
    severity: PerformanceSeverity
    title: str
    description: str
    suggested_action: str
    measured_value: float
    threshold_value: float | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.component_name, str) or not self.component_name.strip():
            raise PerformanceOptimizationError(
                "Recommendation component_name must be non-empty."
            )
        if not isinstance(self.category, OptimizationCategory):
            raise PerformanceOptimizationError(
                "category must be an OptimizationCategory value."
            )
        if not isinstance(self.severity, PerformanceSeverity):
            raise PerformanceOptimizationError(
                "severity must be a PerformanceSeverity value."
            )
        for field_name in ("title", "description", "suggested_action"):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise PerformanceOptimizationError(
                    f"{field_name} must be a non-empty string."
                )
        if (
            isinstance(self.measured_value, bool)
            or not isinstance(self.measured_value, (int, float))
            or self.measured_value < 0
        ):
            raise PerformanceOptimizationError(
                "measured_value must be a non-negative number."
            )
        if self.threshold_value is not None and (
            isinstance(self.threshold_value, bool)
            or not isinstance(self.threshold_value, (int, float))
            or self.threshold_value < 0
        ):
            raise PerformanceOptimizationError(
                "threshold_value must be a non-negative number or None."
            )


@dataclass(frozen=True)
class ComponentPerformanceSummary:
    component_name: str
    measurement_count: int
    total_duration_seconds: float
    average_duration_seconds: float
    maximum_duration_seconds: float
    total_invocations: int
    average_memory_mb: float | None
    maximum_memory_mb: float | None
    cache_hit_rate: float | None

    def __post_init__(self) -> None:
        if not isinstance(self.component_name, str) or not self.component_name.strip():
            raise PerformanceOptimizationError(
                "component_name must be a non-empty string."
            )

        for field_name in (
            "measurement_count",
            "total_invocations",
        ):
            value = getattr(self, field_name)
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise PerformanceOptimizationError(
                    f"{field_name} must be a non-negative integer."
                )

        for field_name in (
            "total_duration_seconds",
            "average_duration_seconds",
            "maximum_duration_seconds",
            "average_memory_mb",
            "maximum_memory_mb",
            "cache_hit_rate",
        ):
            value = getattr(self, field_name)
            if value is None:
                continue
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or value < 0
            ):
                raise PerformanceOptimizationError(
                    f"{field_name} must be non-negative or None."
                )

        if self.cache_hit_rate is not None and self.cache_hit_rate > 1:
            raise PerformanceOptimizationError(
                "cache_hit_rate cannot exceed 1."
            )


@dataclass(frozen=True)
class PerformanceOptimizationReport:
    total_measurements: int
    components_analyzed: int
    total_duration_seconds: float
    average_measurement_duration_seconds: float | None
    recommendations: tuple[PerformanceRecommendation, ...]
    component_summaries: tuple[ComponentPerformanceSummary, ...]

    def __post_init__(self) -> None:
        for field_name in ("total_measurements", "components_analyzed"):
            value = getattr(self, field_name)
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise PerformanceOptimizationError(
                    f"{field_name} must be a non-negative integer."
                )

        if self.components_analyzed != len(self.component_summaries):
            raise PerformanceOptimizationError(
                "components_analyzed must equal the summary count."
            )

        if self.total_measurements < self.components_analyzed:
            raise PerformanceOptimizationError(
                "total_measurements cannot be less than components_analyzed."
            )

        if (
            isinstance(self.total_duration_seconds, bool)
            or not isinstance(self.total_duration_seconds, (int, float))
            or self.total_duration_seconds < 0
        ):
            raise PerformanceOptimizationError(
                "total_duration_seconds must be non-negative."
            )

        if self.average_measurement_duration_seconds is not None and (
            isinstance(self.average_measurement_duration_seconds, bool)
            or not isinstance(self.average_measurement_duration_seconds, (int, float))
            or self.average_measurement_duration_seconds < 0
        ):
            raise PerformanceOptimizationError(
                "average_measurement_duration_seconds must be non-negative or None."
            )

        if not isinstance(self.recommendations, tuple) or not all(
            isinstance(item, PerformanceRecommendation)
            for item in self.recommendations
        ):
            raise PerformanceOptimizationError(
                "recommendations must be a tuple of PerformanceRecommendation objects."
            )

        if not isinstance(self.component_summaries, tuple) or not all(
            isinstance(item, ComponentPerformanceSummary)
            for item in self.component_summaries
        ):
            raise PerformanceOptimizationError(
                "component_summaries must be a tuple of ComponentPerformanceSummary objects."
            )

    @property
    def recommendation_count(self) -> int:
        return len(self.recommendations)

    @property
    def has_recommendations(self) -> bool:
        return bool(self.recommendations)

    @property
    def critical_recommendation_count(self) -> int:
        return sum(
            item.severity is PerformanceSeverity.CRITICAL
            for item in self.recommendations
        )

    @property
    def high_priority_recommendation_count(self) -> int:
        return sum(
            item.severity in (
                PerformanceSeverity.HIGH,
                PerformanceSeverity.CRITICAL,
            )
            for item in self.recommendations
        )

    def get_component_summary(
        self,
        component_name: str,
    ) -> ComponentPerformanceSummary | None:
        if not isinstance(component_name, str) or not component_name.strip():
            raise PerformanceOptimizationError(
                "component_name must be a non-empty string."
            )
        normalized = component_name.strip()
        return next(
            (
                summary
                for summary in self.component_summaries
                if summary.component_name == normalized
            ),
            None,
        )

    def recommendations_by_severity(
        self,
        severity: PerformanceSeverity,
    ) -> tuple[PerformanceRecommendation, ...]:
        if not isinstance(severity, PerformanceSeverity):
            raise PerformanceOptimizationError(
                "severity must be a PerformanceSeverity value."
            )
        return tuple(
            item for item in self.recommendations if item.severity is severity
        )


class PerformanceOptimizationRecommendationService:
    """
    Generates deterministic recommendations from supplied performance metrics.

    The service analyzes measurements; it does not execute profiling,
    benchmark code, or estimate guaranteed performance improvements.
    """

    def __init__(
        self,
        slow_duration_threshold_seconds: float = 1.0,
        high_duration_threshold_seconds: float = 5.0,
        critical_duration_threshold_seconds: float = 15.0,
        high_memory_threshold_mb: float = 256.0,
        critical_memory_threshold_mb: float = 1024.0,
        high_invocation_threshold: int = 1000,
        low_cache_hit_rate_threshold: float = 0.5,
        baseline_regression_threshold: float = 0.25,
    ) -> None:
        thresholds = {
            "slow_duration_threshold_seconds": slow_duration_threshold_seconds,
            "high_duration_threshold_seconds": high_duration_threshold_seconds,
            "critical_duration_threshold_seconds": critical_duration_threshold_seconds,
            "high_memory_threshold_mb": high_memory_threshold_mb,
            "critical_memory_threshold_mb": critical_memory_threshold_mb,
            "high_invocation_threshold": high_invocation_threshold,
            "low_cache_hit_rate_threshold": low_cache_hit_rate_threshold,
            "baseline_regression_threshold": baseline_regression_threshold,
        }

        for name, value in thresholds.items():
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise PerformanceOptimizationError(f"{name} must be numeric.")
            if value < 0:
                raise PerformanceOptimizationError(f"{name} cannot be negative.")

        if high_duration_threshold_seconds < slow_duration_threshold_seconds:
            raise PerformanceOptimizationError(
                "High duration threshold must be at least the slow threshold."
            )
        if critical_duration_threshold_seconds < high_duration_threshold_seconds:
            raise PerformanceOptimizationError(
                "Critical duration threshold must be at least the high threshold."
            )
        if critical_memory_threshold_mb < high_memory_threshold_mb:
            raise PerformanceOptimizationError(
                "Critical memory threshold must be at least the high threshold."
            )
        if high_invocation_threshold < 1:
            raise PerformanceOptimizationError(
                "high_invocation_threshold must be at least 1."
            )
        if not 0 <= low_cache_hit_rate_threshold <= 1:
            raise PerformanceOptimizationError(
                "low_cache_hit_rate_threshold must be between 0 and 1."
            )

        self._slow_duration = float(slow_duration_threshold_seconds)
        self._high_duration = float(high_duration_threshold_seconds)
        self._critical_duration = float(critical_duration_threshold_seconds)
        self._high_memory = float(high_memory_threshold_mb)
        self._critical_memory = float(critical_memory_threshold_mb)
        self._high_invocations = high_invocation_threshold
        self._low_cache_rate = float(low_cache_hit_rate_threshold)
        self._baseline_regression = float(baseline_regression_threshold)

    def analyze(
        self,
        measurements: Iterable[PerformanceMeasurement],
    ) -> PerformanceOptimizationReport:
        if isinstance(measurements, (str, bytes, dict)):
            raise PerformanceOptimizationError(
                "measurements must be an iterable of PerformanceMeasurement objects."
            )

        try:
            records = tuple(measurements)
        except TypeError as exc:
            raise PerformanceOptimizationError(
                "measurements must be iterable."
            ) from exc

        if not all(isinstance(item, PerformanceMeasurement) for item in records):
            raise PerformanceOptimizationError(
                "Every measurement must be a PerformanceMeasurement object."
            )

        grouped: dict[str, list[PerformanceMeasurement]] = {}
        recommendations: list[PerformanceRecommendation] = []

        for measurement in records:
            grouped.setdefault(measurement.component_name.strip(), []).append(
                measurement
            )
            recommendations.extend(self._analyze_measurement(measurement))

        summaries = tuple(
            self._build_summary(name, component_records)
            for name, component_records in sorted(grouped.items())
        )

        total_duration = sum(item.duration_seconds for item in records)

        return PerformanceOptimizationReport(
            total_measurements=len(records),
            components_analyzed=len(grouped),
            total_duration_seconds=total_duration,
            average_measurement_duration_seconds=(
                mean(item.duration_seconds for item in records) if records else None
            ),
            recommendations=tuple(
                sorted(
                    recommendations,
                    key=lambda item: (
                        -self._severity_rank(item.severity),
                        item.component_name,
                        item.category.value,
                    ),
                )
            ),
            component_summaries=summaries,
        )

    def _analyze_measurement(
        self,
        measurement: PerformanceMeasurement,
    ) -> list[PerformanceRecommendation]:
        recommendations: list[PerformanceRecommendation] = []
        component = measurement.component_name.strip()
        duration = float(measurement.duration_seconds)

        if duration > self._slow_duration:
            if duration >= self._critical_duration:
                severity = PerformanceSeverity.CRITICAL
            elif duration >= self._high_duration:
                severity = PerformanceSeverity.HIGH
            else:
                severity = PerformanceSeverity.MEDIUM

            recommendations.append(
                PerformanceRecommendation(
                    component_name=component,
                    category=OptimizationCategory.EXECUTION_TIME,
                    severity=severity,
                    title="Optimize slow execution",
                    description=(
                        f"Measured execution time is {duration} seconds, "
                        f"above the configured slow threshold of "
                        f"{self._slow_duration} seconds."
                    ),
                    suggested_action=(
                        "Profile this component, inspect expensive operations, "
                        "and reduce unnecessary computation or I/O."
                    ),
                    measured_value=duration,
                    threshold_value=self._slow_duration,
                )
            )

        if measurement.memory_mb is not None:
            memory = float(measurement.memory_mb)
            if memory > self._high_memory:
                severity = (
                    PerformanceSeverity.CRITICAL
                    if memory >= self._critical_memory
                    else PerformanceSeverity.HIGH
                )
                recommendations.append(
                    PerformanceRecommendation(
                        component_name=component,
                        category=OptimizationCategory.MEMORY_USAGE,
                        severity=severity,
                        title="Reduce memory consumption",
                        description=(
                            f"Measured memory usage is {memory} MB, "
                            f"above the configured threshold of "
                            f"{self._high_memory} MB."
                        ),
                        suggested_action=(
                            "Inspect object retention, large in-memory collections, "
                            "duplicate data copies, and opportunities for streaming "
                            "or bounded batch processing."
                        ),
                        measured_value=memory,
                        threshold_value=self._high_memory,
                    )
                )

        if measurement.invocation_count > self._high_invocations:
            recommendations.append(
                PerformanceRecommendation(
                    component_name=component,
                    category=OptimizationCategory.HIGH_INVOCATION_COUNT,
                    severity=PerformanceSeverity.MEDIUM,
                    title="Review frequent component invocations",
                    description=(
                        f"The component was invoked {measurement.invocation_count} "
                        f"times, exceeding the configured threshold of "
                        f"{self._high_invocations}."
                    ),
                    suggested_action=(
                        "Review repeated calls, batch compatible work, and consider "
                        "caching stable results where correctness permits."
                    ),
                    measured_value=float(measurement.invocation_count),
                    threshold_value=float(self._high_invocations),
                )
            )

        cache_total = measurement.cache_hits + measurement.cache_misses
        if cache_total > 0:
            hit_rate = measurement.cache_hits / cache_total
            if hit_rate < self._low_cache_rate:
                recommendations.append(
                    PerformanceRecommendation(
                        component_name=component,
                        category=OptimizationCategory.CACHE_EFFICIENCY,
                        severity=PerformanceSeverity.MEDIUM,
                        title="Improve cache effectiveness",
                        description=(
                            f"Cache hit rate is {hit_rate:.2%}, below the configured "
                            f"minimum of {self._low_cache_rate:.2%}."
                        ),
                        suggested_action=(
                            "Review cache keys, expiration policy, cache capacity, "
                            "and whether repeated operations can reuse prior results."
                        ),
                        measured_value=hit_rate,
                        threshold_value=self._low_cache_rate,
                    )
                )

        baseline = measurement.baseline_duration_seconds
        if baseline is not None and baseline > 0:
            regression = (duration - baseline) / baseline
            if regression > self._baseline_regression:
                severity = (
                    PerformanceSeverity.HIGH
                    if regression >= 1.0
                    else PerformanceSeverity.MEDIUM
                )
                recommendations.append(
                    PerformanceRecommendation(
                        component_name=component,
                        category=OptimizationCategory.BASELINE_REGRESSION,
                        severity=severity,
                        title="Investigate performance regression",
                        description=(
                            f"Current duration is {regression:.2%} above the "
                            f"baseline duration of {baseline} seconds."
                        ),
                        suggested_action=(
                            "Compare recent code or configuration changes with the "
                            "baseline and profile the affected execution path."
                        ),
                        measured_value=regression,
                        threshold_value=self._baseline_regression,
                    )
                )

        return recommendations

    @staticmethod
    def _build_summary(
        component_name: str,
        records: list[PerformanceMeasurement],
    ) -> ComponentPerformanceSummary:
        durations = [float(item.duration_seconds) for item in records]
        memory_values = [
            float(item.memory_mb)
            for item in records
            if item.memory_mb is not None
        ]
        total_hits = sum(item.cache_hits for item in records)
        total_misses = sum(item.cache_misses for item in records)
        cache_total = total_hits + total_misses

        return ComponentPerformanceSummary(
            component_name=component_name,
            measurement_count=len(records),
            total_duration_seconds=sum(durations),
            average_duration_seconds=mean(durations),
            maximum_duration_seconds=max(durations),
            total_invocations=sum(item.invocation_count for item in records),
            average_memory_mb=mean(memory_values) if memory_values else None,
            maximum_memory_mb=max(memory_values) if memory_values else None,
            cache_hit_rate=(
                total_hits / cache_total if cache_total else None
            ),
        )

    @staticmethod
    def _severity_rank(severity: PerformanceSeverity) -> int:
        return {
            PerformanceSeverity.LOW: 1,
            PerformanceSeverity.MEDIUM: 2,
            PerformanceSeverity.HIGH: 3,
            PerformanceSeverity.CRITICAL: 4,
        }[severity]