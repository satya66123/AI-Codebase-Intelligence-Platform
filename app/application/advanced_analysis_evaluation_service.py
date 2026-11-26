"""Evaluate the coverage and structural quality of advanced code analysis."""

from dataclasses import dataclass
from enum import Enum
from typing import Any


class AdvancedAnalysisEvaluationError(ValueError):
    """Raised when advanced analysis evaluation receives invalid input."""


class EvaluationLevel(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INSUFFICIENT = "insufficient"


@dataclass(frozen=True)
class AnalysisDimensionScore:
    """Evaluation score for one advanced analysis dimension."""

    name: str
    score: float
    level: EvaluationLevel
    evaluated_items: int
    successful_items: int
    findings: tuple[str, ...] = ()

    def __post_init__(self):
        if not isinstance(self.name, str) or not self.name.strip():
            raise AdvancedAnalysisEvaluationError(
                "Dimension name must be a non-empty string."
            )

        if (
            isinstance(self.score, bool)
            or not isinstance(self.score, (int, float))
            or not 0 <= self.score <= 100
        ):
            raise AdvancedAnalysisEvaluationError(
                "Dimension score must be between 0 and 100."
            )

        if not isinstance(self.level, EvaluationLevel):
            raise AdvancedAnalysisEvaluationError(
                "Dimension level must be an EvaluationLevel."
            )

        for field_name in ("evaluated_items", "successful_items"):
            value = getattr(self, field_name)
            if (
                isinstance(value, bool)
                or not isinstance(value, int)
                or value < 0
            ):
                raise AdvancedAnalysisEvaluationError(
                    f"{field_name} must be a non-negative integer."
                )

        if self.successful_items > self.evaluated_items:
            raise AdvancedAnalysisEvaluationError(
                "Successful items cannot exceed evaluated items."
            )

        if not isinstance(self.findings, tuple):
            raise AdvancedAnalysisEvaluationError(
                "Dimension findings must be a tuple."
            )

        if any(
            not isinstance(item, str) or not item.strip()
            for item in self.findings
        ):
            raise AdvancedAnalysisEvaluationError(
                "Dimension findings must contain non-empty strings."
            )


@dataclass(frozen=True)
class AdvancedAnalysisFinding:
    """A quality or coverage issue identified during evaluation."""

    code: str
    dimension: str
    severity: str
    message: str

    def __post_init__(self):
        for field_name in ("code", "dimension", "severity", "message"):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise AdvancedAnalysisEvaluationError(
                    f"{field_name} must be a non-empty string."
                )


@dataclass(frozen=True)
class AdvancedAnalysisEvaluationResult:
    """Structured evaluation of advanced repository analysis."""

    overall_score: float
    overall_level: EvaluationLevel
    dimensions: tuple[AnalysisDimensionScore, ...]
    findings: tuple[AdvancedAnalysisFinding, ...]
    recommendations: tuple[str, ...]
    evaluated_analyses: int
    completed_analyses: int

    def __post_init__(self):
        if (
            isinstance(self.overall_score, bool)
            or not isinstance(self.overall_score, (int, float))
            or not 0 <= self.overall_score <= 100
        ):
            raise AdvancedAnalysisEvaluationError(
                "Overall score must be between 0 and 100."
            )

        if not isinstance(self.overall_level, EvaluationLevel):
            raise AdvancedAnalysisEvaluationError(
                "Overall level must be an EvaluationLevel."
            )

        if not isinstance(self.dimensions, tuple) or not all(
            isinstance(item, AnalysisDimensionScore)
            for item in self.dimensions
        ):
            raise AdvancedAnalysisEvaluationError(
                "Dimensions must be a tuple of AnalysisDimensionScore objects."
            )

        if not isinstance(self.findings, tuple) or not all(
            isinstance(item, AdvancedAnalysisFinding)
            for item in self.findings
        ):
            raise AdvancedAnalysisEvaluationError(
                "Findings must be a tuple of AdvancedAnalysisFinding objects."
            )

        if not isinstance(self.recommendations, tuple) or any(
            not isinstance(item, str) or not item.strip()
            for item in self.recommendations
        ):
            raise AdvancedAnalysisEvaluationError(
                "Recommendations must be a tuple of non-empty strings."
            )

        for field_name in ("evaluated_analyses", "completed_analyses"):
            value = getattr(self, field_name)
            if (
                isinstance(value, bool)
                or not isinstance(value, int)
                or value < 0
            ):
                raise AdvancedAnalysisEvaluationError(
                    f"{field_name} must be a non-negative integer."
                )

        if self.completed_analyses > self.evaluated_analyses:
            raise AdvancedAnalysisEvaluationError(
                "Completed analyses cannot exceed evaluated analyses."
            )

    @property
    def coverage_percentage(self) -> float:
        if self.evaluated_analyses == 0:
            return 0.0

        return round(
            self.completed_analyses / self.evaluated_analyses * 100,
            2,
        )

    @property
    def is_sufficient(self) -> bool:
        return (
            bool(self.dimensions)
            and self.overall_level is not EvaluationLevel.INSUFFICIENT
        )

    @property
    def dimension_scores(self) -> dict[str, float]:
        return {
            dimension.name: dimension.score
            for dimension in self.dimensions
        }


class AdvancedAnalysisEvaluationService:
    """Evaluate advanced analysis outputs using deterministic evidence metrics."""

    EXPECTED_ANALYSES = (
        "architecture_patterns",
        "module_responsibilities",
        "code_flow",
        "execution_flow",
        "cross_module_relationships",
        "data_flow",
    )

    REPORT_SECTION_COUNT = 8

    def evaluate(
        self,
        investigation_result: Any,
        report: Any = None,
        change_impact_result: Any = None,
        direct_indirect_impact_result: Any = None,
    ) -> AdvancedAnalysisEvaluationResult:
        """Evaluate investigation, report, and optional impact-analysis results."""

        self._validate_investigation(investigation_result)

        dimensions = []
        findings = []
        recommendations = []

        architecture = investigation_result.architecture_patterns
        responsibilities = investigation_result.module_responsibilities
        code_flow = investigation_result.code_flow
        execution_flow = investigation_result.execution_flow
        cross_module = investigation_result.cross_module_relationships
        data_flow = investigation_result.data_flow

        dimensions.append(
            self._evaluate_architecture(architecture, responsibilities)
        )
        dimensions.append(self._evaluate_code_flow(code_flow))
        dimensions.append(self._evaluate_execution_flow(execution_flow))
        dimensions.append(self._evaluate_cross_module(cross_module))
        dimensions.append(self._evaluate_data_flow(data_flow))

        if change_impact_result is not None:
            dimensions.append(
                self._evaluate_change_impact(change_impact_result)
            )

        if direct_indirect_impact_result is not None:
            dimensions.append(
                self._evaluate_direct_indirect_impact(
                    direct_indirect_impact_result
                )
            )

        if report is not None:
            dimensions.append(self._evaluate_report(report))

        for dimension in dimensions:
            findings.extend(
                self._findings_from_dimension(dimension)
            )
            recommendations.extend(
                self._recommendations_for_dimension(dimension)
            )

        overall_score = round(
            sum(item.score for item in dimensions) / len(dimensions),
            2,
        ) if dimensions else 0.0

        completed = sum(
            1
            for name in self.EXPECTED_ANALYSES
            if self._analysis_completed(investigation_result, name)
        )

        return AdvancedAnalysisEvaluationResult(
            overall_score=overall_score,
            overall_level=self._level(overall_score),
            dimensions=tuple(dimensions),
            findings=tuple(findings),
            recommendations=tuple(dict.fromkeys(recommendations)),
            evaluated_analyses=len(self.EXPECTED_ANALYSES),
            completed_analyses=completed,
        )

    @staticmethod
    def _validate_investigation(result):
        required = (
            "total_files",
            "analyzed_files",
            "skipped_files",
            "architecture_patterns",
            "module_responsibilities",
            "code_flow",
            "execution_flow",
            "cross_module_relationships",
            "data_flow",
        )

        if result is None:
            raise AdvancedAnalysisEvaluationError(
                "investigation_result cannot be None."
            )

        if any(not hasattr(result, field) for field in required):
            raise AdvancedAnalysisEvaluationError(
                "Investigation result is missing required analysis fields."
            )

        for field_name in ("total_files", "analyzed_files", "skipped_files"):
            value = getattr(result, field_name)
            if (
                isinstance(value, bool)
                or not isinstance(value, int)
                or value < 0
            ):
                raise AdvancedAnalysisEvaluationError(
                    f"Investigation {field_name} must be a non-negative integer."
                )

        if result.analyzed_files + result.skipped_files > result.total_files:
            raise AdvancedAnalysisEvaluationError(
                "Investigation file counts are inconsistent."
            )

    def _evaluate_architecture(self, architecture, responsibilities):
        classified = self._integer(responsibilities, "classified_modules")
        total_modules = self._integer(responsibilities, "total_modules")
        patterns = self._integer(architecture, "patterns_detected")

        if total_modules:
            score = classified / total_modules * 100
            evaluated = total_modules
            successful = min(classified, total_modules)
        else:
            score = 100.0
            evaluated = 1
            successful = 1

        messages = []
        if total_modules and classified < total_modules:
            messages.append(
                f"{total_modules - classified} module(s) were not classified."
            )

        if patterns == 0:
            messages.append(
                "No architecture patterns were detected; this is not "
                "automatically evidence of an architecture defect."
            )

        return self._dimension(
            "architecture",
            score,
            evaluated,
            successful,
            messages,
        )

    def _evaluate_code_flow(self, result):
        total = self._integer(result, "total_calls")
        resolved = self._integer(result, "resolved_calls")
        unresolved = self._integer(result, "unresolved_calls")

        return self._resolution_dimension(
            "code_flow",
            total,
            resolved,
            unresolved,
        )

    def _evaluate_execution_flow(self, result):
        resolved = self._integer(result, "resolved_calls")
        unresolved = self._integer(result, "unresolved_calls")
        total = resolved + unresolved

        if total == 0:
            score = 100.0
            evaluated = 1
            successful = 1
        else:
            score = resolved / total * 100
            evaluated = total
            successful = resolved

        messages = []
        if unresolved:
            messages.append(
                f"{unresolved} execution reference(s) remain unresolved."
            )

        return self._dimension(
            "execution_flow",
            score,
            evaluated,
            successful,
            messages,
        )

    def _evaluate_cross_module(self, result):
        resolved = self._integer(result, "resolved_calls")
        unresolved = self._integer(result, "unresolved_calls")
        return self._resolution_dimension(
            "cross_module_relationships",
            resolved + unresolved,
            resolved,
            unresolved,
        )

    def _evaluate_data_flow(self, results):
        if not isinstance(results, (tuple, list)):
            raise AdvancedAnalysisEvaluationError(
                "data_flow must be a tuple or list of per-file results."
            )

        if not results:
            return self._dimension(
                "data_flow",
                100.0,
                1,
                1,
                ("No per-file data-flow results were supplied.",),
            )

        analyzed = 0
        messages = []

        for item in results:
            if not hasattr(item, "analyzed") or not hasattr(item, "file_path"):
                raise AdvancedAnalysisEvaluationError(
                    "Every data-flow result must expose file_path and analyzed."
                )

            if not isinstance(item.analyzed, bool):
                raise AdvancedAnalysisEvaluationError(
                    "Data-flow analyzed values must be booleans."
                )

            if item.analyzed:
                analyzed += 1
            else:
                messages.append(
                    f"Data-flow analysis was skipped for {item.file_path}."
                )

        score = analyzed / len(results) * 100

        return self._dimension(
            "data_flow",
            score,
            len(results),
            analyzed,
            messages,
        )

    def _evaluate_change_impact(self, result):
        findings = self._tuple_attribute(result, "findings")
        total = len(findings)
        complete = 0

        required = (
            "source_file",
            "affected_file",
            "relationship_type",
            "changed_target",
            "affected_entity",
            "reason",
        )

        messages = []

        for item in findings:
            if all(
                isinstance(getattr(item, field, None), str)
                and getattr(item, field).strip()
                for field in required
            ):
                complete += 1
            else:
                messages.append(
                    "A change-impact finding is missing traceability details."
                )

        if total == 0:
            return self._dimension(
                "change_impact",
                100.0,
                1,
                1,
                ("No impact findings were identified for the supplied targets.",),
            )

        return self._dimension(
            "change_impact",
            complete / total * 100,
            total,
            complete,
            messages,
        )

    def _evaluate_direct_indirect_impact(self, result):
        findings = self._tuple_attribute(result, "findings")
        total = len(findings)
        complete = 0
        messages = []

        for item in findings:
            path = getattr(item, "path", None)
            relationship_types = getattr(item, "relationship_types", None)

            valid_path = (
                isinstance(path, tuple)
                and len(path) >= 2
                and all(isinstance(node, str) and node.strip() for node in path)
            )
            valid_relationships = (
                isinstance(relationship_types, tuple)
                and len(relationship_types) == len(path) - 1
            )

            if valid_path and valid_relationships:
                complete += 1
            else:
                messages.append(
                    "An impact finding has an incomplete relationship path."
                )

        if total == 0:
            return self._dimension(
                "direct_indirect_impact",
                100.0,
                1,
                1,
                ("No direct or indirect impact findings were identified.",),
            )

        return self._dimension(
            "direct_indirect_impact",
            complete / total * 100,
            total,
            complete,
            messages,
        )

    def _evaluate_report(self, report):
        sections = self._tuple_attribute(report, "sections")
        recommendations = self._tuple_attribute(report, "recommendations")

        if not hasattr(report, "report_text"):
            raise AdvancedAnalysisEvaluationError(
                "Report must expose report_text."
            )

        if not isinstance(report.report_text, str) or not report.report_text.strip():
            raise AdvancedAnalysisEvaluationError(
                "Report text must be a non-empty string."
            )

        score = min(
            len(sections) / self.REPORT_SECTION_COUNT * 100,
            100.0,
        )

        messages = []
        if len(sections) < self.REPORT_SECTION_COUNT:
            messages.append(
                f"Report contains {len(sections)} of "
                f"{self.REPORT_SECTION_COUNT} expected sections."
            )

        if not recommendations:
            messages.append("The report contains no recommendations.")

        return self._dimension(
            "report",
            score,
            self.REPORT_SECTION_COUNT,
            min(len(sections), self.REPORT_SECTION_COUNT),
            messages,
        )

    def _resolution_dimension(self, name, total, resolved, unresolved):
        if resolved + unresolved > total:
            raise AdvancedAnalysisEvaluationError(
                f"{name} resolved and unresolved counts exceed total calls."
            )

        if total == 0:
            score = 100.0
            evaluated = 1
            successful = 1
        else:
            score = resolved / total * 100
            evaluated = total
            successful = resolved

        messages = []
        if unresolved:
            messages.append(
                f"{unresolved} of {total} relationship(s) remain unresolved."
            )

        return self._dimension(
            name,
            score,
            evaluated,
            successful,
            messages,
        )

    @staticmethod
    def _dimension(name, score, evaluated, successful, messages=()):
        score = round(max(0.0, min(100.0, float(score))), 2)

        return AnalysisDimensionScore(
            name=name,
            score=score,
            level=AdvancedAnalysisEvaluationService._level(score),
            evaluated_items=evaluated,
            successful_items=successful,
            findings=tuple(dict.fromkeys(messages)),
        )

    @staticmethod
    def _level(score):
        if score >= 85:
            return EvaluationLevel.HIGH
        if score >= 70:
            return EvaluationLevel.MEDIUM
        if score > 0:
            return EvaluationLevel.LOW
        return EvaluationLevel.INSUFFICIENT

    @staticmethod
    def _integer(result, attribute):
        value = getattr(result, attribute, 0)

        if (
            isinstance(value, bool)
            or not isinstance(value, int)
            or value < 0
        ):
            raise AdvancedAnalysisEvaluationError(
                f"{attribute} must be a non-negative integer."
            )

        return value

    @staticmethod
    def _tuple_attribute(result, attribute):
        value = getattr(result, attribute, ())

        if not isinstance(value, (tuple, list)):
            raise AdvancedAnalysisEvaluationError(
                f"{attribute} must be a tuple or list."
            )

        return tuple(value)

    @staticmethod
    def _analysis_completed(result, name):
        value = getattr(result, name, None)
        return value is not None

    @staticmethod
    def _findings_from_dimension(dimension):
        findings = []

        for message in dimension.findings:
            findings.append(
                AdvancedAnalysisFinding(
                    code=f"{dimension.name.upper()}_QUALITY",
                    dimension=dimension.name,
                    severity=(
                        "high"
                        if dimension.score < 50
                        else "medium"
                    ),
                    message=message,
                )
            )

        return findings

    @staticmethod
    def _recommendations_for_dimension(dimension):
        if dimension.score >= 85:
            return ()

        recommendations = {
            "architecture": (
                "Review unclassified modules and improve responsibility evidence."
            ),
            "code_flow": (
                "Review unresolved calls and improve call-target resolution."
            ),
            "execution_flow": (
                "Investigate unresolved function and method execution references."
            ),
            "cross_module_relationships": (
                "Review unresolved cross-module relationships."
            ),
            "data_flow": (
                "Improve data-flow coverage for skipped source files."
            ),
            "change_impact": (
                "Ensure each change-impact finding includes complete traceability details."
            ),
            "direct_indirect_impact": (
                "Ensure impact findings contain complete relationship paths."
            ),
            "report": (
                "Complete the architecture report sections and include actionable recommendations."
            ),
        }

        recommendation = recommendations.get(dimension.name)
        return (recommendation,) if recommendation else ()