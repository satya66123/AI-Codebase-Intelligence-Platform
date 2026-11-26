
"""Release readiness and final validation service."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any


class ReleaseReadinessError(Exception):
    """Raised when release readiness input validation fails."""

    def __init__(self, message: str, stage: str = "input_validation"):
        super().__init__(message)
        self.stage = stage


@dataclass(frozen=True)
class ReleaseReadinessCheck:
    """Represents an individual release readiness check."""

    name: str
    passed: bool
    details: str

    def __post_init__(self):
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("Check name must be a non-empty string.")

        if not isinstance(self.passed, bool):
            raise ValueError("Check result must be a boolean.")

        if not isinstance(self.details, str) or not self.details.strip():
            raise ValueError("Check details must be a non-empty string.")


@dataclass(frozen=True)
class ReleaseReadinessReport:
    """Immutable final release readiness report."""

    project_name: str
    checks: tuple[ReleaseReadinessCheck, ...]
    generated_at: str

    def __post_init__(self):
        if not isinstance(self.project_name, str) or not self.project_name.strip():
            raise ValueError("Project name must be a non-empty string.")

        if not isinstance(self.checks, tuple):
            raise ValueError("Checks must be stored as a tuple.")

        if not all(
            isinstance(check, ReleaseReadinessCheck)
            for check in self.checks
        ):
            raise ValueError("All checks must be ReleaseReadinessCheck objects.")

        if not isinstance(self.generated_at, str) or not self.generated_at.strip():
            raise ValueError("Generated timestamp must be a non-empty string.")

    @property
    def total_checks(self) -> int:
        return len(self.checks)

    @property
    def passed_checks(self) -> int:
        return sum(check.passed for check in self.checks)

    @property
    def failed_checks(self) -> int:
        return self.total_checks - self.passed_checks

    @property
    def is_ready(self) -> bool:
        return self.total_checks > 0 and self.failed_checks == 0

    @property
    def readiness_percentage(self) -> float:
        if not self.checks:
            return 0.0

        return round(
            (self.passed_checks / self.total_checks) * 100,
            2,
        )

    @property
    def failed_check_names(self) -> tuple[str, ...]:
        return tuple(
            check.name
            for check in self.checks
            if not check.passed
        )

    @property
    def status(self) -> str:
        return "READY" if self.is_ready else "NOT READY"


class ReleaseReadinessFinalValidationService:
    """Performs final release readiness validation."""

    REQUIRED_CHECKS = (
        "project_metadata",
        "development_phases",
        "implemented_components",
        "test_validation",
        "provider_integration",
        "application_reliability",
        "final_documentation",
    )

    COMPLETED_STATUSES = {
        "completed",
        "complete",
    }

    def validate(
        self,
        project_info: Mapping[str, Any],
        phases: Sequence[Mapping[str, Any]],
        components: Sequence[Mapping[str, Any]],
        test_summary: Mapping[str, Any],
        provider_validation_passed: bool,
        reliability_failure_count: int,
        documentation_complete: bool,
    ) -> ReleaseReadinessReport:
        """Validate all release readiness requirements."""

        self._validate_inputs(
            project_info=project_info,
            phases=phases,
            components=components,
            test_summary=test_summary,
            provider_validation_passed=provider_validation_passed,
            reliability_failure_count=reliability_failure_count,
            documentation_complete=documentation_complete,
        )

        checks = (
            self._check_project_metadata(project_info),
            self._check_phases(phases),
            self._check_components(components),
            self._check_tests(test_summary),
            self._check_providers(provider_validation_passed),
            self._check_reliability(reliability_failure_count),
            self._check_documentation(documentation_complete),
        )

        from datetime import datetime, timezone

        generated_at = datetime.now(timezone.utc).isoformat()

        return ReleaseReadinessReport(
            project_name=project_info["project_name"].strip(),
            checks=checks,
            generated_at=generated_at,
        )

    def _validate_inputs(
        self,
        project_info,
        phases,
        components,
        test_summary,
        provider_validation_passed,
        reliability_failure_count,
        documentation_complete,
    ):
        if not isinstance(project_info, Mapping):
            raise ReleaseReadinessError(
                "Project information must be a mapping."
            )

        project_name = project_info.get("project_name")
        version = project_info.get("version")

        if not isinstance(project_name, str) or not project_name.strip():
            raise ReleaseReadinessError(
                "A valid project name is required."
            )

        if not isinstance(version, str) or not version.strip():
            raise ReleaseReadinessError(
                "A valid project version is required."
            )

        self._validate_status_collection(phases, "phases")
        self._validate_status_collection(components, "components")

        if not isinstance(test_summary, Mapping):
            raise ReleaseReadinessError(
                "Test summary must be a mapping."
            )

        passed = test_summary.get("tests_passed")
        failed = test_summary.get("tests_failed")

        if (
            isinstance(passed, bool)
            or not isinstance(passed, int)
            or passed < 0
        ):
            raise ReleaseReadinessError(
                "tests_passed must be a non-negative integer."
            )

        if (
            isinstance(failed, bool)
            or not isinstance(failed, int)
            or failed < 0
        ):
            raise ReleaseReadinessError(
                "tests_failed must be a non-negative integer."
            )

        if not isinstance(provider_validation_passed, bool):
            raise ReleaseReadinessError(
                "Provider validation result must be a boolean."
            )

        if (
            isinstance(reliability_failure_count, bool)
            or not isinstance(reliability_failure_count, int)
            or reliability_failure_count < 0
        ):
            raise ReleaseReadinessError(
                "Reliability failure count must be a non-negative integer."
            )

        if not isinstance(documentation_complete, bool):
            raise ReleaseReadinessError(
                "Documentation completion result must be a boolean."
            )

    def _validate_status_collection(self, values, label):
        if (
            not isinstance(values, Sequence)
            or isinstance(values, (str, bytes))
            or not values
        ):
            raise ReleaseReadinessError(
                f"{label} must be a non-empty sequence."
            )

        for index, item in enumerate(values):
            if not isinstance(item, Mapping):
                raise ReleaseReadinessError(
                    f"Every {label} entry must be a mapping."
                )

            name = item.get("name")
            status = item.get("status")

            if not isinstance(name, str) or not name.strip():
                raise ReleaseReadinessError(
                    f"Every {label} entry requires a valid name."
                )

            if not isinstance(status, str) or not status.strip():
                raise ReleaseReadinessError(
                    f"Every {label} entry requires a valid status."
                )

    def _check_project_metadata(self, project_info):
        return ReleaseReadinessCheck(
            name="Project metadata",
            passed=True,
            details=(
                f"Project '{project_info['project_name'].strip()}' "
                f"has version '{project_info['version'].strip()}'."
            ),
        )

    def _check_phases(self, phases):
        incomplete = [
            item["name"].strip()
            for item in phases
            if item["status"].strip().lower()
            not in self.COMPLETED_STATUSES
        ]

        if incomplete:
            return ReleaseReadinessCheck(
                name="Development phases",
                passed=False,
                details=(
                    "Incomplete phases: " + ", ".join(incomplete)
                ),
            )

        return ReleaseReadinessCheck(
            name="Development phases",
            passed=True,
            details=f"All {len(phases)} development phases are completed.",
        )

    def _check_components(self, components):
        incomplete = [
            item["name"].strip()
            for item in components
            if item["status"].strip().lower()
            not in self.COMPLETED_STATUSES
        ]

        if incomplete:
            return ReleaseReadinessCheck(
                name="Implemented components",
                passed=False,
                details=(
                    "Incomplete components: " + ", ".join(incomplete)
                ),
            )

        return ReleaseReadinessCheck(
            name="Implemented components",
            passed=True,
            details=f"All {len(components)} components are completed.",
        )

    def _check_tests(self, test_summary):
        passed = test_summary["tests_passed"]
        failed = test_summary["tests_failed"]

        success = passed > 0 and failed == 0

        if success:
            details = f"{passed} tests passed and zero tests failed."
        else:
            details = (
                f"Test validation failed: {passed} passed, "
                f"{failed} failed."
            )

        return ReleaseReadinessCheck(
            name="Test validation",
            passed=success,
            details=details,
        )

    def _check_providers(self, provider_validation_passed):
        return ReleaseReadinessCheck(
            name="Provider integration",
            passed=provider_validation_passed,
            details=(
                "All configured provider integrations passed validation."
                if provider_validation_passed
                else "Provider integration validation failed."
            ),
        )

    def _check_reliability(self, reliability_failure_count):
        success = reliability_failure_count == 0

        return ReleaseReadinessCheck(
            name="Application reliability",
            passed=success,
            details=(
                "No application reliability failures were recorded."
                if success
                else (
                    f"{reliability_failure_count} application "
                    "reliability failures were recorded."
                )
            ),
        )

    def _check_documentation(self, documentation_complete):
        return ReleaseReadinessCheck(
            name="Final documentation",
            passed=documentation_complete,
            details=(
                "Final project documentation is complete."
                if documentation_complete
                else "Final project documentation is incomplete."
            ),
        )
