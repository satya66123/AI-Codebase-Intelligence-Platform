
"""Assess repository dependency health from dependency-analysis results."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from enum import Enum
from typing import Any

from appy.application.circular_dependency_detection_service import (
    CircularDependencyDetectionResult,
)
from appy.application.dependency_consistency_validation_service import (
    DependencyConsistencyValidationResult,
    DependencyConsistencySeverity,
)
from appy.application.import_reference_validation_service import (
    ImportReferenceSeverity,
    ImportReferenceStatus,
    ImportReferenceValidationResult,
)


class DependencyHealthAssessmentError(ValueError):
    """Raised when dependency health assessment receives invalid input."""


class DependencyHealthStatus(str, Enum):
    HEALTHY = "healthy"
    NEEDS_ATTENTION = "needs_attention"
    UNHEALTHY = "unhealthy"


class DependencyHealthSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass(frozen=True)
class DependencyHealthFinding:
    """One dependency health finding."""

    code: str
    message: str
    severity: DependencyHealthSeverity
    affected_count: int

    def __post_init__(self) -> None:
        if not isinstance(self.code, str) or not self.code.strip():
            raise DependencyHealthAssessmentError(
                "Finding code must be a non-empty string."
            )
        if not isinstance(self.message, str) or not self.message.strip():
            raise DependencyHealthAssessmentError(
                "Finding message must be a non-empty string."
            )
        if not isinstance(self.severity, DependencyHealthSeverity):
            raise DependencyHealthAssessmentError(
                "Finding severity must be a DependencyHealthSeverity."
            )
        if (
            isinstance(self.affected_count, bool)
            or not isinstance(self.affected_count, int)
            or self.affected_count < 1
        ):
            raise DependencyHealthAssessmentError(
                "affected_count must be a positive integer."
            )


@dataclass(frozen=True)
class DependencyHealthAssessment:
    """Overall dependency health assessment."""

    health_score: int
    status: DependencyHealthStatus
    total_dependencies: int
    internal_dependencies: int
    external_dependencies: int
    unresolved_dependencies: int
    invalid_references: int
    consistency_errors: int
    consistency_warnings: int
    circular_dependency_count: int
    findings: tuple[DependencyHealthFinding, ...]

    def __post_init__(self) -> None:
        if (
            isinstance(self.health_score, bool)
            or not isinstance(self.health_score, int)
            or not 0 <= self.health_score <= 100
        ):
            raise DependencyHealthAssessmentError(
                "health_score must be an integer between 0 and 100."
            )
        if not isinstance(self.status, DependencyHealthStatus):
            raise DependencyHealthAssessmentError(
                "status must be a DependencyHealthStatus."
            )

        count_fields = (
            self.total_dependencies,
            self.internal_dependencies,
            self.external_dependencies,
            self.unresolved_dependencies,
            self.invalid_references,
            self.consistency_errors,
            self.consistency_warnings,
            self.circular_dependency_count,
        )
        if any(
            isinstance(value, bool) or not isinstance(value, int) or value < 0
            for value in count_fields
        ):
            raise DependencyHealthAssessmentError(
                "Assessment counts must be non-negative integers."
            )
        if not isinstance(self.findings, tuple):
            raise DependencyHealthAssessmentError("findings must be a tuple.")
        if any(
            not isinstance(item, DependencyHealthFinding)
            for item in self.findings
        ):
            raise DependencyHealthAssessmentError(
                "Every finding must be a DependencyHealthFinding."
            )

    @property
    def is_healthy(self) -> bool:
        return self.status == DependencyHealthStatus.HEALTHY

    @property
    def has_issues(self) -> bool:
        return bool(self.findings)

    @property
    def critical_findings(self) -> tuple[DependencyHealthFinding, ...]:
        return tuple(
            finding
            for finding in self.findings
            if finding.severity == DependencyHealthSeverity.CRITICAL
        )

    @property
    def error_findings(self) -> tuple[DependencyHealthFinding, ...]:
        return tuple(
            finding
            for finding in self.findings
            if finding.severity == DependencyHealthSeverity.ERROR
        )

    @property
    def warning_findings(self) -> tuple[DependencyHealthFinding, ...]:
        return tuple(
            finding
            for finding in self.findings
            if finding.severity == DependencyHealthSeverity.WARNING
        )

    @property
    def info_findings(self) -> tuple[DependencyHealthFinding, ...]:
        return tuple(
            finding
            for finding in self.findings
            if finding.severity == DependencyHealthSeverity.INFO
        )

    @property
    def finding_count(self) -> int:
        return len(self.findings)


class DependencyHealthAssessmentService:
    """Combine consistency, import-reference, and cycle results into health."""

    def assess(
        self,
        consistency_result: DependencyConsistencyValidationResult | None = None,
        import_reference_result: ImportReferenceValidationResult | None = None,
        circular_dependency_result: CircularDependencyDetectionResult | None = None,
    ) -> DependencyHealthAssessment:
        self._validate_optional_result(
            consistency_result,
            DependencyConsistencyValidationResult,
            "consistency_result",
        )
        self._validate_optional_result(
            import_reference_result,
            ImportReferenceValidationResult,
            "import_reference_result",
        )
        self._validate_optional_result(
            circular_dependency_result,
            CircularDependencyDetectionResult,
            "circular_dependency_result",
        )

        findings: list[DependencyHealthFinding] = []

        total_dependencies = 0
        internal_dependencies = 0
        external_dependencies = 0
        unresolved_dependencies = 0
        invalid_references = 0
        consistency_errors = 0
        consistency_warnings = 0
        circular_dependency_count = 0

        if consistency_result is not None:
            total_dependencies = max(
                total_dependencies, consistency_result.imports_checked
            )
            consistency_errors = consistency_result.error_count
            consistency_warnings = consistency_result.warning_count

            if consistency_errors:
                findings.append(
                    DependencyHealthFinding(
                        code="DEPENDENCY_CONSISTENCY_ERRORS",
                        message=(
                            "Dependency consistency validation found "
                            "one or more errors."
                        ),
                        severity=DependencyHealthSeverity.ERROR,
                        affected_count=consistency_errors,
                    )
                )

            if consistency_warnings:
                findings.append(
                    DependencyHealthFinding(
                        code="DEPENDENCY_CONSISTENCY_WARNINGS",
                        message=(
                            "Dependency consistency validation reported "
                            "warnings that should be reviewed."
                        ),
                        severity=DependencyHealthSeverity.WARNING,
                        affected_count=consistency_warnings,
                    )
                )

        if import_reference_result is not None:
            total_dependencies = max(
                total_dependencies, import_reference_result.total_imports
            )
            invalid_references = import_reference_result.invalid_imports
            unresolved_dependencies = import_reference_result.unresolved_imports
            external_dependencies = import_reference_result.external_imports
            internal_dependencies = import_reference_result.valid_imports

            if invalid_references:
                findings.append(
                    DependencyHealthFinding(
                        code="INVALID_IMPORT_REFERENCES",
                        message=(
                            "Import reference validation found references "
                            "that do not resolve to known repository modules "
                            "or exported symbols."
                        ),
                        severity=DependencyHealthSeverity.ERROR,
                        affected_count=invalid_references,
                    )
                )

            if unresolved_dependencies:
                findings.append(
                    DependencyHealthFinding(
                        code="UNRESOLVED_IMPORT_REFERENCES",
                        message=(
                            "Some imports could not be resolved with the "
                            "available repository package context."
                        ),
                        severity=DependencyHealthSeverity.WARNING,
                        affected_count=unresolved_dependencies,
                    )
                )

            if external_dependencies:
                findings.append(
                    DependencyHealthFinding(
                        code="EXTERNAL_IMPORT_REFERENCES",
                        message=(
                            "External imports were identified. Review "
                            "their dependency declarations and availability."
                        ),
                        severity=DependencyHealthSeverity.INFO,
                        affected_count=external_dependencies,
                    )
                )

        if circular_dependency_result is not None:
            circular_dependency_count = circular_dependency_result.cycle_count

            if circular_dependency_count:
                findings.append(
                    DependencyHealthFinding(
                        code="CIRCULAR_DEPENDENCIES",
                        message=(
                            "Circular dependencies were detected between "
                            "repository modules."
                        ),
                        severity=DependencyHealthSeverity.CRITICAL,
                        affected_count=circular_dependency_count,
                    )
                )

        findings.sort(
            key=lambda finding: (
                self._severity_order(finding.severity),
                finding.code,
            )
        )

        score = self._calculate_score(
            invalid_references=invalid_references,
            consistency_errors=consistency_errors,
            consistency_warnings=consistency_warnings,
            unresolved_dependencies=unresolved_dependencies,
            circular_dependency_count=circular_dependency_count,
        )
        status = self._determine_status(score, findings)

        return DependencyHealthAssessment(
            health_score=score,
            status=status,
            total_dependencies=total_dependencies,
            internal_dependencies=internal_dependencies,
            external_dependencies=external_dependencies,
            unresolved_dependencies=unresolved_dependencies,
            invalid_references=invalid_references,
            consistency_errors=consistency_errors,
            consistency_warnings=consistency_warnings,
            circular_dependency_count=circular_dependency_count,
            findings=tuple(findings),
        )

    @staticmethod
    def _validate_optional_result(
        value: Any,
        expected_type: type,
        field_name: str,
    ) -> None:
        if value is not None and not isinstance(value, expected_type):
            raise DependencyHealthAssessmentError(
                f"{field_name} must be an instance of "
                f"{expected_type.__name__} or None."
            )

    @staticmethod
    def _severity_order(severity: DependencyHealthSeverity) -> int:
        order = {
            DependencyHealthSeverity.CRITICAL: 0,
            DependencyHealthSeverity.ERROR: 1,
            DependencyHealthSeverity.WARNING: 2,
            DependencyHealthSeverity.INFO: 3,
        }
        return order[severity]

    @staticmethod
    def _calculate_score(
        *,
        invalid_references: int,
        consistency_errors: int,
        consistency_warnings: int,
        unresolved_dependencies: int,
        circular_dependency_count: int,
    ) -> int:
        """Calculate a bounded, deterministic score from reported risks.

        The score is intentionally rule-based, not a statistical probability.
        Each finding count reduces the score, with cycles and confirmed
        invalid references carrying the largest penalties.
        """
        penalty = (
            invalid_references * 15
            + consistency_errors * 12
            + consistency_warnings * 3
            + unresolved_dependencies * 4
            + circular_dependency_count * 20
        )
        return max(0, min(100, 100 - penalty))

    @staticmethod
    def _determine_status(
        score: int,
        findings: list[DependencyHealthFinding],
    ) -> DependencyHealthStatus:
        if any(
            finding.severity == DependencyHealthSeverity.CRITICAL
            for finding in findings
        ):
            return DependencyHealthStatus.UNHEALTHY

        if any(
            finding.severity == DependencyHealthSeverity.ERROR
            for finding in findings
        ):
            return DependencyHealthStatus.UNHEALTHY

        if score < 80 or any(
            finding.severity == DependencyHealthSeverity.WARNING
            for finding in findings
        ):
            return DependencyHealthStatus.NEEDS_ATTENTION

        return DependencyHealthStatus.HEALTHY
