
"""Orchestrates advanced repository investigation services."""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from appy.application.affected_component_identification_service import (
    AffectedComponentIdentificationService,
)
from appy.application.advanced_code_flow_tracing_service import (
    AdvancedCodeFlowTracingService,
)
from appy.application.architecture_pattern_detection_service import (
    ArchitecturePatternDetectionService,
)
from appy.application.data_flow_analysis_service import (
    DataFlowAnalysisService,
)
from appy.application.dependency_health_assessment_service import (
    DependencyHealthAssessmentService,
)
from appy.application.direct_indirect_impact_detection_service import (
    DirectIndirectImpactDetectionService,
)
from appy.application.function_method_execution_path_service import (
    FunctionMethodExecutionPathService,
)
from appy.application.module_responsibility_analysis_service import (
    ModuleResponsibilityAnalysisService,
)
from appy.application.cross_module_relationship_analysis_service import (
    CrossModuleRelationshipAnalysisService,
)


class AdvancedCodeInvestigationError(ValueError):
    """Raised when an advanced investigation cannot be completed."""

    def __init__(self, message, stage=None):
        super().__init__(message)
        self.stage = stage


@dataclass(frozen=True)
class AdvancedCodeInvestigationResult:
    total_files: int
    analyzed_files: int
    skipped_files: int
    architecture_patterns: Any
    module_responsibilities: Any
    code_flow: Any
    execution_flow: Any
    cross_module_relationships: Any
    data_flow: Any
    investigation_summary: tuple

    def __post_init__(self):
        for field in (
            "total_files",
            "analyzed_files",
            "skipped_files",
        ):
            value = getattr(self, field)

            if (
                isinstance(value, bool)
                or not isinstance(value, int)
                or value < 0
            ):
                raise AdvancedCodeInvestigationError(
                    f"{field} must be a non-negative integer."
                )

        if self.analyzed_files + self.skipped_files > self.total_files:
            raise AdvancedCodeInvestigationError(
                "Analyzed and skipped file counts cannot exceed total files."
            )

        if not isinstance(self.investigation_summary, tuple):
            raise AdvancedCodeInvestigationError(
                "investigation_summary must be a tuple."
            )

        if any(
            not isinstance(item, str) or not item.strip()
            for item in self.investigation_summary
        ):
            raise AdvancedCodeInvestigationError(
                "Investigation summary entries must be non-empty strings."
            )

    @property
    def has_findings(self):
        return any(
            (
                self._has_results(self.architecture_patterns),
                self._has_results(self.module_responsibilities),
                self._has_results(self.code_flow),
                self._has_results(self.execution_flow),
                self._has_results(self.cross_module_relationships),
                self._has_results(self.data_flow),
            )
        )

    @property
    def healthy(self):
        return self.skipped_files == 0

    @property
    def completed_analyses(self):
        return (
            "architecture_patterns",
            "module_responsibilities",
            "code_flow",
            "execution_flow",
            "cross_module_relationships",
            "data_flow",
        )

    @staticmethod
    def _has_results(result):
        if result is None:
            return False

        for attribute in (
            "has_patterns",
            "has_unclassified_modules",
            "has_execution_flows",
            "has_cross_module_relationships",
            "has_data_flow",
            "has_affected_components",
        ):
            value = getattr(result, attribute, None)
            if value is True:
                return True

        for attribute in (
            "findings",
            "patterns",
            "traces",
            "cross_module_calls",
            "paths",
            "nodes",
            "components",
        ):
            value = getattr(result, attribute, None)
            if value:
                return True

        return False


class AdvancedCodeInvestigationAgent:
    """Coordinates existing analysis services into one investigation."""

    def __init__(
        self,
        architecture_service=None,
        responsibility_service=None,
        code_flow_service=None,
        execution_flow_service=None,
        cross_module_service=None,
        data_flow_service=None,
    ):
        self.architecture_service = (
            architecture_service
            or ArchitecturePatternDetectionService()
        )
        self.responsibility_service = (
            responsibility_service
            or ModuleResponsibilityAnalysisService()
        )
        self.code_flow_service = (
            code_flow_service
            or AdvancedCodeFlowTracingService()
        )
        self.execution_flow_service = (
            execution_flow_service
            or FunctionMethodExecutionPathService()
        )
        self.cross_module_service = (
            cross_module_service
            or CrossModuleRelationshipAnalysisService()
        )
        self.data_flow_service = (
            data_flow_service
            or DataFlowAnalysisService()
        )

    def investigate(
        self,
        parsed_sources,
        source_files=None,
        code_entities=(),
        dependencies=(),
        call_graphs=(),
        entry_points=None,
        max_depth=10,
    ):
        parsed_sources = self._validate_parsed_sources(parsed_sources)
        source_files = self._validate_source_files(
            source_files,
            parsed_sources,
        )
        code_entities = self._validate_collection(
            code_entities,
            "code_entities",
        )
        dependencies = self._validate_collection(
            dependencies,
            "dependencies",
        )
        call_graphs = self._validate_collection(
            call_graphs,
            "call_graphs",
        )
        entry_points = self._validate_entry_points(entry_points)
        max_depth = self._validate_max_depth(max_depth)

        total_files = len(source_files)
        python_sources = tuple(
            parsed_sources.values()
        )

        # Stage 1: Architecture pattern detection.
        architecture_result = self._run_stage(
            "architecture_pattern_detection",
            self.architecture_service.analyze,
            source_files=source_files,
            code_entities=code_entities,
            dependencies=dependencies,
            call_graphs=call_graphs,
        )

        # Stage 2: Module responsibility analysis.
        responsibility_result = self._run_stage(
            "module_responsibility_analysis",
            self.responsibility_service.analyze,
            source_files=source_files,
            code_entities=code_entities,
            dependencies=dependencies,
            call_graphs=call_graphs,
        )

        # Stage 3: Advanced code-flow tracing.
        code_flow_result = self._run_stage(
            "advanced_code_flow_tracing",
            self.code_flow_service.analyze,
            parsed_sources=parsed_sources,
            entry_points=entry_points,
            max_depth=max_depth,
        )

        # Stage 4: Function and method execution paths.
        execution_result = self._run_stage(
            "function_method_execution_paths",
            self.execution_flow_service.analyze,
            parsed_sources=parsed_sources,
            entry_points=entry_points,
            max_depth=max_depth,
        )

        # Stage 5: Cross-module relationships.
        cross_module_result = self._run_stage(
            "cross_module_relationship_analysis",
            self.cross_module_service.analyze,
            parsed_sources=parsed_sources,
        )

        # Stage 6: Data-flow analysis.
        data_flow_result = self._run_stage(
            "data_flow_analysis",
            self.data_flow_service.analyze,
            parsed_sources=python_sources,
        )

        analyzed_files, skipped_files = self._file_counts(
            source_files,
            parsed_sources,
            data_flow_result,
        )

        summary = self._build_summary(
            architecture_result,
            responsibility_result,
            code_flow_result,
            execution_result,
            cross_module_result,
            data_flow_result,
        )

        return AdvancedCodeInvestigationResult(
            total_files=total_files,
            analyzed_files=analyzed_files,
            skipped_files=skipped_files,
            architecture_patterns=architecture_result,
            module_responsibilities=responsibility_result,
            code_flow=code_flow_result,
            execution_flow=execution_result,
            cross_module_relationships=cross_module_result,
            data_flow=data_flow_result,
            investigation_summary=summary,
        )

    @staticmethod
    def _run_stage(stage, callback, **kwargs):
        try:
            return callback(**kwargs)
        except AdvancedCodeInvestigationError:
            raise
        except Exception as exc:
            raise AdvancedCodeInvestigationError(
                f"Investigation failed during {stage}: {exc}",
                stage=stage,
            ) from exc

    @staticmethod
    def _validate_parsed_sources(parsed_sources):
        if not isinstance(parsed_sources, Mapping):
            raise AdvancedCodeInvestigationError(
                "parsed_sources must be a mapping of filenames to ParsedSource objects."
            )

        if not parsed_sources:
            raise AdvancedCodeInvestigationError(
                "parsed_sources must not be empty."
            )

        normalized = {}

        for filename, parsed_source in parsed_sources.items():
            if not isinstance(filename, str) or not filename.strip():
                raise AdvancedCodeInvestigationError(
                    "Parsed source filenames must be non-empty strings."
                )

            if parsed_source is None:
                raise AdvancedCodeInvestigationError(
                    f"Parsed source for '{filename}' cannot be None."
                )

            if not hasattr(parsed_source, "language"):
                raise AdvancedCodeInvestigationError(
                    f"Parsed source for '{filename}' must expose language."
                )

            if not hasattr(parsed_source, "filename"):
                raise AdvancedCodeInvestigationError(
                    f"Parsed source for '{filename}' must expose filename."
                )

            if parsed_source.filename != filename:
                raise AdvancedCodeInvestigationError(
                    f"Parsed source filename mismatch for '{filename}'."
                )

            normalized[filename] = parsed_source

        return dict(sorted(normalized.items()))

    @staticmethod
    def _validate_source_files(source_files, parsed_sources):
        if source_files is None:
            return tuple(parsed_sources.keys())

        if isinstance(
            source_files,
            (str, bytes, dict, set, frozenset),
        ):
            raise AdvancedCodeInvestigationError(
                "source_files must be an ordered iterable of filenames."
            )

        try:
            values = tuple(source_files)
        except TypeError as exc:
            raise AdvancedCodeInvestigationError(
                "source_files must be iterable."
            ) from exc

        if any(
            not isinstance(item, str) or not item.strip()
            for item in values
        ):
            raise AdvancedCodeInvestigationError(
                "source_files must contain non-empty strings."
            )

        if len(values) != len(set(values)):
            raise AdvancedCodeInvestigationError(
                "source_files must not contain duplicates."
            )

        if set(values) != set(parsed_sources):
            raise AdvancedCodeInvestigationError(
                "source_files must match the parsed_sources filenames."
            )

        return tuple(sorted(values))

    @staticmethod
    def _validate_collection(values, label):
        if values is None or isinstance(
            values,
            (str, bytes, dict, set, frozenset),
        ):
            raise AdvancedCodeInvestigationError(
                f"{label} must be an ordered iterable."
            )

        try:
            return tuple(values)
        except TypeError as exc:
            raise AdvancedCodeInvestigationError(
                f"{label} must be iterable."
            ) from exc

    @staticmethod
    def _validate_entry_points(entry_points):
        if entry_points is None:
            return None

        if isinstance(
            entry_points,
            (str, bytes, dict, set, frozenset),
        ):
            raise AdvancedCodeInvestigationError(
                "entry_points must be an ordered iterable."
            )

        try:
            values = tuple(entry_points)
        except TypeError as exc:
            raise AdvancedCodeInvestigationError(
                "entry_points must be iterable."
            ) from exc

        if any(
            not isinstance(item, str) or not item.strip()
            for item in values
        ):
            raise AdvancedCodeInvestigationError(
                "entry_points must contain non-empty strings."
            )

        if len(values) != len(set(values)):
            raise AdvancedCodeInvestigationError(
                "entry_points must not contain duplicates."
            )

        return values

    @staticmethod
    def _validate_max_depth(max_depth):
        if (
            isinstance(max_depth, bool)
            or not isinstance(max_depth, int)
            or max_depth < 1
        ):
            raise AdvancedCodeInvestigationError(
                "max_depth must be a positive integer."
            )

        return max_depth

    @staticmethod
    def _file_counts(source_files, parsed_sources, data_flow_result):
        analyzed = set()
        skipped = set()

        for item in getattr(data_flow_result, "results", ()):
            filename = getattr(item, "file_path", None)

            if not isinstance(filename, str):
                continue

            if getattr(item, "analyzed", False):
                analyzed.add(filename)
            else:
                skipped.add(filename)

        if analyzed or skipped:
            return len(analyzed), len(skipped)

        # When the data-flow result does not expose per-file results,
        # use the parsed-source language metadata conservatively.
        for filename, parsed_source in parsed_sources.items():
            language = getattr(parsed_source, "language", "")
            language = getattr(language, "value", language)

            if isinstance(language, str) and language.lower() in {
                "python",
                "py",
            }:
                analyzed.add(filename)
            else:
                skipped.add(filename)

        return len(analyzed), len(skipped)

    @staticmethod
    def _build_summary(
        architecture,
        responsibilities,
        code_flow,
        execution,
        cross_module,
        data_flow,
    ):
        summary = []

        summary.append(
            "Architecture patterns detected: "
            f"{getattr(architecture, 'patterns_detected', 0)}."
        )

        summary.append(
            "Classified modules: "
            f"{getattr(responsibilities, 'classified_modules', 0)}."
        )

        summary.append(
            "Code-flow analysis completed."
        )

        summary.append(
            "Execution-flow analysis completed."
        )

        summary.append(
            "Cross-module relationship analysis completed."
        )

        summary.append(
            "Data-flow analysis completed."
        )

        return tuple(summary)
