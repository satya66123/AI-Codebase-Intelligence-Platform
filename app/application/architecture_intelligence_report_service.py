
"""Creates structured architecture intelligence reports."""

from dataclasses import dataclass
from enum import Enum


class ArchitectureIntelligenceReportError(ValueError):
    """Raised when report generation input is invalid."""


class ReportSectionType(str, Enum):
    OVERVIEW = "overview"
    ARCHITECTURE_PATTERNS = "architecture_patterns"
    MODULE_RESPONSIBILITIES = "module_responsibilities"
    CODE_FLOW = "code_flow"
    EXECUTION_FLOW = "execution_flow"
    CROSS_MODULE_RELATIONSHIPS = "cross_module_relationships"
    DATA_FLOW = "data_flow"
    RECOMMENDATIONS = "recommendations"


@dataclass(frozen=True)
class ArchitectureReportSection:
    section_type: ReportSectionType
    title: str
    summary: str
    findings: tuple = ()

    def __post_init__(self):
        if not isinstance(self.section_type, ReportSectionType):
            raise ArchitectureIntelligenceReportError(
                "section_type must be a ReportSectionType."
            )

        for field in ("title", "summary"):
            value = getattr(self, field)
            if not isinstance(value, str) or not value.strip():
                raise ArchitectureIntelligenceReportError(
                    f"{field} must be a non-empty string."
                )

        if not isinstance(self.findings, tuple):
            raise ArchitectureIntelligenceReportError(
                "findings must be a tuple."
            )

        if any(
            not isinstance(item, str) or not item.strip()
            for item in self.findings
        ):
            raise ArchitectureIntelligenceReportError(
                "Section findings must contain non-empty strings."
            )


@dataclass(frozen=True)
class ArchitectureIntelligenceReport:
    title: str
    total_files: int
    analyzed_files: int
    skipped_files: int
    sections: tuple
    recommendations: tuple
    report_text: str

    def __post_init__(self):
        if not isinstance(self.title, str) or not self.title.strip():
            raise ArchitectureIntelligenceReportError(
                "title must be a non-empty string."
            )

        for field in ("total_files", "analyzed_files", "skipped_files"):
            value = getattr(self, field)
            if (
                isinstance(value, bool)
                or not isinstance(value, int)
                or value < 0
            ):
                raise ArchitectureIntelligenceReportError(
                    f"{field} must be a non-negative integer."
                )

        if self.analyzed_files + self.skipped_files > self.total_files:
            raise ArchitectureIntelligenceReportError(
                "Analyzed and skipped files cannot exceed total files."
            )

        if not isinstance(self.sections, tuple):
            raise ArchitectureIntelligenceReportError(
                "sections must be a tuple."
            )

        if not all(
            isinstance(item, ArchitectureReportSection)
            for item in self.sections
        ):
            raise ArchitectureIntelligenceReportError(
                "sections must contain ArchitectureReportSection objects."
            )

        if not isinstance(self.recommendations, tuple):
            raise ArchitectureIntelligenceReportError(
                "recommendations must be a tuple."
            )

        if any(
            not isinstance(item, str) or not item.strip()
            for item in self.recommendations
        ):
            raise ArchitectureIntelligenceReportError(
                "recommendations must contain non-empty strings."
            )

        if not isinstance(self.report_text, str) or not self.report_text.strip():
            raise ArchitectureIntelligenceReportError(
                "report_text must be a non-empty string."
            )

    @property
    def section_count(self):
        return len(self.sections)

    @property
    def has_recommendations(self):
        return bool(self.recommendations)

    @property
    def is_complete(self):
        return self.skipped_files == 0

    def get_section(self, section_type):
        if isinstance(section_type, str):
            try:
                section_type = ReportSectionType(section_type)
            except ValueError:
                return None

        return next(
            (
                section
                for section in self.sections
                if section.section_type is section_type
            ),
            None,
        )


class ArchitectureIntelligenceReportService:
    """Builds an evidence-based report from an investigation result."""

    REPORT_TITLE = "Architecture Intelligence Report"

    def generate(self, investigation_result):
        self._validate_investigation_result(investigation_result)

        architecture = investigation_result.architecture_patterns
        responsibilities = investigation_result.module_responsibilities
        code_flow = investigation_result.code_flow
        execution_flow = investigation_result.execution_flow
        cross_module = investigation_result.cross_module_relationships
        data_flow = investigation_result.data_flow

        sections = (
            self._overview_section(investigation_result),
            self._architecture_section(architecture),
            self._responsibility_section(responsibilities),
            self._code_flow_section(code_flow),
            self._execution_section(execution_flow),
            self._cross_module_section(cross_module),
            self._data_flow_section(data_flow),
        )

        recommendations = self._recommendations(
            architecture,
            responsibilities,
            code_flow,
            execution_flow,
            cross_module,
            data_flow,
            investigation_result,
        )

        sections += (
            ArchitectureReportSection(
                section_type=ReportSectionType.RECOMMENDATIONS,
                title="Recommendations",
                summary=(
                    f"{len(recommendations)} recommendation(s) "
                    "identified from available investigation evidence."
                ),
                findings=recommendations,
            ),
        )

        report_text = self._render_text(
            self.REPORT_TITLE,
            sections,
            investigation_result,
        )

        return ArchitectureIntelligenceReport(
            title=self.REPORT_TITLE,
            total_files=investigation_result.total_files,
            analyzed_files=investigation_result.analyzed_files,
            skipped_files=investigation_result.skipped_files,
            sections=sections,
            recommendations=recommendations,
            report_text=report_text,
        )

    @staticmethod
    def _validate_investigation_result(result):
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
            raise ArchitectureIntelligenceReportError(
                "investigation_result cannot be None."
            )

        if any(not hasattr(result, field) for field in required):
            raise ArchitectureIntelligenceReportError(
                "investigation_result does not expose the required "
                "advanced investigation fields."
            )

        for field in ("total_files", "analyzed_files", "skipped_files"):
            value = getattr(result, field)
            if (
                isinstance(value, bool)
                or not isinstance(value, int)
                or value < 0
            ):
                raise ArchitectureIntelligenceReportError(
                    f"Investigation {field} must be a non-negative integer."
                )

        if (
            result.analyzed_files + result.skipped_files
            > result.total_files
        ):
            raise ArchitectureIntelligenceReportError(
                "Investigation file counts are inconsistent."
            )

    def _overview_section(self, result):
        summary = (
            f"Investigation covered {result.total_files} file(s): "
            f"{result.analyzed_files} analyzed and "
            f"{result.skipped_files} skipped."
        )

        findings = (
            f"Total files: {result.total_files}",
            f"Analyzed files: {result.analyzed_files}",
            f"Skipped files: {result.skipped_files}",
        )

        return ArchitectureReportSection(
            ReportSectionType.OVERVIEW,
            "Investigation Overview",
            summary,
            findings,
        )

    def _architecture_section(self, result):
        patterns = self._items(result, "findings")
        pattern_count = self._integer(result, "patterns_detected")

        findings = []

        for item in patterns:
            pattern = self._enum_value(
                getattr(item, "pattern", "unknown")
            )
            confidence = self._enum_value(
                getattr(item, "confidence", "unknown")
            )
            evidence_count = self._integer(item, "evidence_count")
            files = self._string_items(
                getattr(item, "affected_files", ())
            )

            findings.append(
                f"{pattern}: confidence={confidence}, "
                f"evidence={evidence_count}, "
                f"affected_files={len(files)}"
            )

        if not findings:
            findings.append("No architecture patterns were detected.")

        return ArchitectureReportSection(
            ReportSectionType.ARCHITECTURE_PATTERNS,
            "Architecture Patterns",
            f"{pattern_count} architecture pattern(s) detected.",
            tuple(findings),
        )

    def _responsibility_section(self, result):
        findings = []

        for item in self._items(result, "findings"):
            responsibility = self._enum_value(
                getattr(item, "responsibility", "unknown")
            )
            confidence = self._enum_value(
                getattr(item, "confidence", "unknown")
            )

            findings.append(
                f"{getattr(item, 'file_path', 'unknown')}: "
                f"{responsibility} responsibility "
                f"(confidence={confidence})"
            )

        unclassified = self._string_items(
            getattr(result, "unclassified_files", ())
        )

        for file_path in unclassified:
            findings.append(
                f"{file_path}: responsibility could not be classified."
            )

        classified = self._integer(result, "classified_modules")
        total = self._integer(result, "total_modules")

        if not findings:
            findings.append("No module responsibility findings available.")

        return ArchitectureReportSection(
            ReportSectionType.MODULE_RESPONSIBILITIES,
            "Module Responsibilities",
            f"{classified} of {total} module(s) classified.",
            tuple(findings),
        )

    def _code_flow_section(self, result):
        findings = []

        traces = self._items(result, "traces")
        for trace in traces:
            entry = getattr(trace, "entry_point", "unknown")
            depth = self._integer(trace, "depth")
            recursive = bool(getattr(trace, "is_recursive", False))

            findings.append(
                f"Entry point {entry}: depth={depth}, "
                f"recursive={recursive}."
            )

        unresolved = self._items(result, "unresolved_calls")
        findings.extend(
            self._describe_item(item)
            for item in unresolved
        )

        if not findings:
            findings.append(
                "No code-flow trace details were reported."
            )

        return ArchitectureReportSection(
            ReportSectionType.CODE_FLOW,
            "Advanced Code Flow",
            (
                f"{len(traces)} trace(s) and "
                f"{len(unresolved)} unresolved call(s) reported."
            ),
            tuple(findings),
        )

    def _execution_section(self, result):
        paths = self._items(result, "execution_paths")
        unresolved = self._items(result, "unresolved_references")

        findings = [
            self._describe_item(item)
            for item in paths
        ]

        findings.extend(
            self._describe_item(item)
            for item in unresolved
        )

        total_paths = self._integer(
            result,
            "total_execution_paths",
            len(paths),
        )

        if not findings:
            findings.append(
                "No execution-path details were reported."
            )

        return ArchitectureReportSection(
            ReportSectionType.EXECUTION_FLOW,
            "Function and Method Execution Flow",
            (
                f"{total_paths} execution path(s) and "
                f"{len(unresolved)} unresolved reference(s) reported."
            ),
            tuple(findings),
        )

    def _cross_module_section(self, result):
        relationships = self._items(result, "module_relationships")
        unresolved = self._items(result, "unresolved_references")

        findings = []

        for item in relationships:
            source = getattr(item, "source_module", "unknown")
            target = getattr(item, "target_module", "unknown")
            count = self._integer(item, "relationship_count")

            findings.append(
                f"{source} -> {target}: {count} relationship(s)."
            )

        findings.extend(
            self._describe_item(item)
            for item in unresolved
        )

        if not findings:
            findings.append(
                "No cross-module relationship details were reported."
            )

        resolved = self._integer(result, "resolved_calls")
        unresolved_count = self._integer(result, "unresolved_calls")

        return ArchitectureReportSection(
            ReportSectionType.CROSS_MODULE_RELATIONSHIPS,
            "Cross-Module Relationships",
            (
                f"{resolved} resolved call(s) and "
                f"{unresolved_count} unresolved call(s)."
            ),
            tuple(findings),
        )

    def _data_flow_section(self, result):
        results = self._items(result, "results")

        findings = []

        if results:
            for item in results:
                file_path = getattr(item, "file_path", "unknown")
                nodes = self._integer(item, "total_nodes")
                edges = self._integer(item, "total_edges")
                paths = self._integer(item, "total_paths")
                analyzed = bool(getattr(item, "analyzed", False))

                findings.append(
                    f"{file_path}: analyzed={analyzed}, "
                    f"nodes={nodes}, edges={edges}, paths={paths}."
                )
        else:
            nodes = self._integer(result, "total_nodes")
            edges = self._integer(result, "total_edges")
            paths = self._integer(result, "total_paths")

            if nodes or edges or paths:
                findings.append(
                    f"Data-flow totals: nodes={nodes}, "
                    f"edges={edges}, paths={paths}."
                )

        if not findings:
            findings.append(
                "No per-file data-flow details were reported."
            )

        return ArchitectureReportSection(
            ReportSectionType.DATA_FLOW,
            "Data Flow",
            f"{len(results)} per-file data-flow result(s) available.",
            tuple(findings),
        )

    def _recommendations(
        self,
        architecture,
        responsibilities,
        code_flow,
        execution,
        cross_module,
        data_flow,
        investigation,
    ):
        recommendations = []

        unclassified = self._string_items(
            getattr(responsibilities, "unclassified_files", ())
        )

        if unclassified:
            recommendations.append(
                "Review unclassified modules and document their intended responsibilities."
            )

        low_confidence = [
            item
            for item in self._items(architecture, "findings")
            if self._enum_value(
                getattr(item, "confidence", "")
            ) == "low"
        ]

        if low_confidence:
            recommendations.append(
                "Review low-confidence architecture pattern detections manually."
            )

        if self._integer(cross_module, "unresolved_calls") > 0:
            recommendations.append(
                "Investigate unresolved cross-module references and verify their targets."
            )

        if self._items(code_flow, "unresolved_calls"):
            recommendations.append(
                "Review unresolved calls in the advanced code-flow traces."
            )

        if self._items(execution, "unresolved_references"):
            recommendations.append(
                "Resolve or document unresolved function and method execution references."
            )

        if self._integer(execution, "maximum_execution_depth") > 10:
            recommendations.append(
                "Review deep execution paths for excessive call-chain complexity."
            )

        skipped = investigation.skipped_files

        if skipped:
            recommendations.append(
                "Review skipped files and add language-specific analysis support where required."
            )

        if not recommendations:
            recommendations.append(
                "No immediate structural recommendations were identified from the available evidence."
            )

        return tuple(dict.fromkeys(recommendations))

    def _render_text(self, title, sections, investigation):
        lines = [
            title,
            "=" * len(title),
            "",
            (
                f"Files: {investigation.total_files} | "
                f"Analyzed: {investigation.analyzed_files} | "
                f"Skipped: {investigation.skipped_files}"
            ),
            "",
        ]

        for section in sections:
            lines.extend(
                (
                    section.title,
                    "-" * len(section.title),
                    section.summary,
                )
            )

            lines.extend(
                f"- {finding}"
                for finding in section.findings
            )

            lines.append("")

        return "\n".join(lines).rstrip() + "\n"

    @staticmethod
    def _items(result, attribute):
        value = getattr(result, attribute, ()) if result is not None else ()

        if value is None:
            return ()

        if isinstance(value, (str, bytes, dict)):
            return ()

        try:
            return tuple(value)
        except TypeError:
            return ()

    @staticmethod
    def _string_items(values):
        if values is None or isinstance(values, (str, bytes, dict)):
            return ()

        try:
            items = tuple(values)
        except TypeError:
            return ()

        return tuple(
            item for item in items
            if isinstance(item, str) and item.strip()
        )

    @staticmethod
    def _integer(result, attribute, default=0):
        value = getattr(result, attribute, default) if result is not None else default

        if (
            isinstance(value, bool)
            or not isinstance(value, int)
            or value < 0
        ):
            return default

        return value

    @staticmethod
    def _enum_value(value):
        return getattr(value, "value", value)

    @staticmethod
    def _describe_item(item):
        if isinstance(item, str):
            return item

        if hasattr(item, "__dict__"):
            values = sorted(item.__dict__.items())
            return ", ".join(
                f"{key}={value}"
                for key, value in values
            )

        return str(item)
