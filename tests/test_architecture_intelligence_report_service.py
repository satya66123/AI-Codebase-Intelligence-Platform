
from types import SimpleNamespace

import pytest

from appy.application.architecture_intelligence_report_service import (
    ArchitectureIntelligenceReport,
    ArchitectureIntelligenceReportError,
    ArchitectureIntelligenceReportService,
    ArchitectureReportSection,
    ReportSectionType,
)


@pytest.fixture
def service():
    return ArchitectureIntelligenceReportService()


def investigation_result(
    architecture=None,
    responsibilities=None,
    code_flow=None,
    execution=None,
    cross_module=None,
    data_flow=None,
    total_files=3,
    analyzed_files=3,
    skipped_files=0,
):
    return SimpleNamespace(
        total_files=total_files,
        analyzed_files=analyzed_files,
        skipped_files=skipped_files,
        architecture_patterns=architecture or SimpleNamespace(
            patterns_detected=0,
            findings=(),
        ),
        module_responsibilities=responsibilities or SimpleNamespace(
            total_modules=0,
            classified_modules=0,
            unclassified_files=(),
            findings=(),
        ),
        code_flow=code_flow or SimpleNamespace(
            traces=(),
            unresolved_calls=(),
        ),
        execution_flow=execution or SimpleNamespace(
            execution_paths=(),
            unresolved_references=(),
            total_execution_paths=0,
            maximum_execution_depth=0,
        ),
        cross_module_relationships=cross_module or SimpleNamespace(
            module_relationships=(),
            unresolved_references=(),
            resolved_calls=0,
            unresolved_calls=0,
        ),
        data_flow=data_flow or SimpleNamespace(
            results=(),
        ),
    )


def test_generate_returns_report(service):
    result = service.generate(investigation_result())

    assert isinstance(result, ArchitectureIntelligenceReport)


def test_report_has_expected_title(service):
    result = service.generate(investigation_result())

    assert result.title == "Architecture Intelligence Report"


def test_report_preserves_file_counts(service):
    result = service.generate(
        investigation_result(
            total_files=10,
            analyzed_files=8,
            skipped_files=2,
        )
    )

    assert result.total_files == 10
    assert result.analyzed_files == 8
    assert result.skipped_files == 2


def test_report_contains_eight_sections(service):
    result = service.generate(investigation_result())

    assert result.section_count == 8


def test_report_contains_all_section_types(service):
    result = service.generate(investigation_result())

    assert tuple(
        section.section_type for section in result.sections
    ) == (
        ReportSectionType.OVERVIEW,
        ReportSectionType.ARCHITECTURE_PATTERNS,
        ReportSectionType.MODULE_RESPONSIBILITIES,
        ReportSectionType.CODE_FLOW,
        ReportSectionType.EXECUTION_FLOW,
        ReportSectionType.CROSS_MODULE_RELATIONSHIPS,
        ReportSectionType.DATA_FLOW,
        ReportSectionType.RECOMMENDATIONS,
    )


def test_overview_section_contains_file_counts(service):
    result = service.generate(
        investigation_result(
            total_files=5,
            analyzed_files=4,
            skipped_files=1,
        )
    )

    section = result.get_section(ReportSectionType.OVERVIEW)

    assert "5 file(s)" in section.summary
    assert "4 analyzed" in section.summary
    assert "1 skipped" in section.summary


def test_architecture_section_reports_patterns(service):
    pattern = SimpleNamespace(
        pattern=SimpleNamespace(value="layered_architecture"),
        confidence=SimpleNamespace(value="high"),
        evidence_count=4,
        affected_files=("appy/domain.py", "appy/services.py"),
    )

    result = service.generate(
        investigation_result(
            architecture=SimpleNamespace(
                patterns_detected=1,
                findings=(pattern,),
            )
        )
    )

    section = result.get_section(
        ReportSectionType.ARCHITECTURE_PATTERNS
    )

    assert "1 architecture pattern" in section.summary
    assert "layered_architecture" in section.findings[0]
    assert "confidence=high" in section.findings[0]


def test_architecture_section_handles_no_patterns(service):
    result = service.generate(investigation_result())

    section = result.get_section(
        ReportSectionType.ARCHITECTURE_PATTERNS
    )

    assert "No architecture patterns" in section.findings[0]


def test_module_section_reports_classified_modules(service):
    finding = SimpleNamespace(
        file_path="appy/services/user.py",
        responsibility=SimpleNamespace(value="service"),
        confidence=SimpleNamespace(value="high"),
    )

    result = service.generate(
        investigation_result(
            responsibilities=SimpleNamespace(
                total_modules=2,
                classified_modules=1,
                unclassified_files=("appy/unknown.py",),
                findings=(finding,),
            )
        )
    )

    section = result.get_section(
        ReportSectionType.MODULE_RESPONSIBILITIES
    )

    assert "1 of 2 module(s) classified" in section.summary
    assert any(
        "appy/services/user.py" in item
        for item in section.findings
    )
    assert any(
        "appy/unknown.py" in item
        for item in section.findings
    )


def test_code_flow_section_reports_traces(service):
    trace = SimpleNamespace(
        entry_point="main.main",
        depth=4,
        is_recursive=False,
    )

    result = service.generate(
        investigation_result(
            code_flow=SimpleNamespace(
                traces=(trace,),
                unresolved_calls=(),
            )
        )
    )

    section = result.get_section(ReportSectionType.CODE_FLOW)

    assert "1 trace(s)" in section.summary
    assert any(
        "main.main" in item
        for item in section.findings
    )


def test_code_flow_section_reports_unresolved_calls(service):
    unresolved = SimpleNamespace(
        caller="main.main",
        callee="unknown_function",
        reason="Target not found",
    )

    result = service.generate(
        investigation_result(
            code_flow=SimpleNamespace(
                traces=(),
                unresolved_calls=(unresolved,),
            )
        )
    )

    section = result.get_section(ReportSectionType.CODE_FLOW)

    assert "unknown_function" in section.findings[0]


def test_execution_section_reports_paths(service):
    path = SimpleNamespace(
        entry_point="main.main",
        depth=3,
        is_recursive=False,
    )

    result = service.generate(
        investigation_result(
            execution=SimpleNamespace(
                execution_paths=(path,),
                unresolved_references=(),
                total_execution_paths=1,
            )
        )
    )

    section = result.get_section(ReportSectionType.EXECUTION_FLOW)

    assert "1 execution path(s)" in section.summary
    assert "main.main" in section.findings[0]


def test_execution_section_reports_unresolved_references(service):
    reference = SimpleNamespace(
        source_file="main.py",
        caller="main",
        callee="missing_function",
        reason="Target not found",
    )

    result = service.generate(
        investigation_result(
            execution=SimpleNamespace(
                execution_paths=(),
                unresolved_references=(reference,),
                total_execution_paths=0,
            )
        )
    )

    section = result.get_section(ReportSectionType.EXECUTION_FLOW)

    assert any(
        "missing_function" in item
        for item in section.findings
    )


def test_cross_module_section_reports_relationships(service):
    relationship = SimpleNamespace(
        source_module="appy.main",
        target_module="appy.services",
        relationship_count=3,
    )

    result = service.generate(
        investigation_result(
            cross_module=SimpleNamespace(
                module_relationships=(relationship,),
                unresolved_references=(),
                resolved_calls=3,
                unresolved_calls=0,
            )
        )
    )

    section = result.get_section(
        ReportSectionType.CROSS_MODULE_RELATIONSHIPS
    )

    assert "3 resolved call(s)" in section.summary
    assert "appy.main -> appy.services" in section.findings[0]


def test_cross_module_section_reports_unresolved_references(service):
    reference = SimpleNamespace(
        source_module="appy.main",
        callee="missing",
        reason="No target entity",
    )

    result = service.generate(
        investigation_result(
            cross_module=SimpleNamespace(
                module_relationships=(),
                unresolved_references=(reference,),
                resolved_calls=0,
                unresolved_calls=1,
            )
        )
    )

    section = result.get_section(
        ReportSectionType.CROSS_MODULE_RELATIONSHIPS
    )

    assert any(
        "missing" in item
        for item in section.findings
    )


def test_data_flow_section_reports_per_file_results(service):
    file_result = SimpleNamespace(
        file_path="main.py",
        analyzed=True,
        total_nodes=5,
        total_edges=4,
        total_paths=4,
    )

    result = service.generate(
        investigation_result(
            data_flow=SimpleNamespace(
                results=(file_result,),
            )
        )
    )

    section = result.get_section(ReportSectionType.DATA_FLOW)

    assert "1 per-file" in section.summary
    assert "nodes=5" in section.findings[0]
    assert "edges=4" in section.findings[0]


def test_data_flow_section_reports_aggregate_counts(service):
    result = service.generate(
        investigation_result(
            data_flow=SimpleNamespace(
                total_nodes=10,
                total_edges=8,
                total_paths=6,
            )
        )
    )

    section = result.get_section(ReportSectionType.DATA_FLOW)

    assert "nodes=10" in section.findings[0]


def test_report_generates_recommendation_for_unclassified_modules(service):
    result = service.generate(
        investigation_result(
            responsibilities=SimpleNamespace(
                total_modules=2,
                classified_modules=1,
                unclassified_files=("unknown.py",),
                findings=(),
            )
        )
    )

    assert any(
        "unclassified modules" in item
        for item in result.recommendations
    )


def test_report_generates_recommendation_for_unresolved_calls(service):
    result = service.generate(
        investigation_result(
            cross_module=SimpleNamespace(
                module_relationships=(),
                unresolved_references=(),
                resolved_calls=1,
                unresolved_calls=2,
            )
        )
    )

    assert any(
        "unresolved cross-module references" in item
        for item in result.recommendations
    )


def test_report_generates_recommendation_for_unresolved_code_flow(service):
    result = service.generate(
        investigation_result(
            code_flow=SimpleNamespace(
                traces=(),
                unresolved_calls=("unknown call",),
            )
        )
    )

    assert any(
        "unresolved calls" in item
        for item in result.recommendations
    )


def test_report_generates_recommendation_for_unresolved_execution(service):
    result = service.generate(
        investigation_result(
            execution=SimpleNamespace(
                execution_paths=(),
                unresolved_references=("unknown reference",),
                total_execution_paths=0,
                maximum_execution_depth=0,
            )
        )
    )

    assert any(
        "unresolved function and method" in item
        for item in result.recommendations
    )


def test_report_generates_recommendation_for_skipped_files(service):
    result = service.generate(
        investigation_result(
            total_files=3,
            analyzed_files=2,
            skipped_files=1,
        )
    )

    assert any(
        "skipped files" in item
        for item in result.recommendations
    )


def test_report_generates_default_recommendation(service):
    result = service.generate(investigation_result())

    assert result.has_recommendations
    assert any(
        "No immediate structural recommendations" in item
        for item in result.recommendations
    )


def test_report_text_contains_title(service):
    result = service.generate(investigation_result())

    assert result.report_text.startswith(
        "Architecture Intelligence Report"
    )


def test_report_text_contains_all_section_titles(service):
    result = service.generate(investigation_result())

    for section in result.sections:
        assert section.title in result.report_text


def test_report_text_ends_with_newline(service):
    result = service.generate(investigation_result())

    assert result.report_text.endswith("\n")


def test_get_section_accepts_string(service):
    result = service.generate(investigation_result())

    section = result.get_section("overview")

    assert section is not None
    assert section.section_type is ReportSectionType.OVERVIEW


def test_get_section_returns_none_for_unknown_type(service):
    result = service.generate(investigation_result())

    assert result.get_section("unknown") is None


def test_report_is_deterministic(service):
    source = investigation_result()

    first = service.generate(source)
    second = service.generate(source)

    assert first == second
    assert first.report_text == second.report_text


def test_rejects_none_investigation_result(service):
    with pytest.raises(ArchitectureIntelligenceReportError):
        service.generate(None)


def test_rejects_missing_investigation_fields(service):
    with pytest.raises(ArchitectureIntelligenceReportError):
        service.generate(SimpleNamespace(total_files=1))


@pytest.mark.parametrize(
    "field,value",
    [
        ("total_files", -1),
        ("analyzed_files", -1),
        ("skipped_files", -1),
        ("total_files", True),
    ],
)
def test_rejects_invalid_investigation_counts(service, field, value):
    source = investigation_result()
    setattr(source, field, value)

    with pytest.raises(ArchitectureIntelligenceReportError):
        service.generate(source)


def test_rejects_inconsistent_investigation_counts(service):
    source = investigation_result(
        total_files=1,
        analyzed_files=1,
        skipped_files=1,
    )

    with pytest.raises(ArchitectureIntelligenceReportError):
        service.generate(source)


def test_section_model_rejects_invalid_type():
    with pytest.raises(ArchitectureIntelligenceReportError):
        ArchitectureReportSection(
            "overview",
            "Title",
            "Summary",
            (),
        )


def test_section_model_rejects_empty_title():
    with pytest.raises(ArchitectureIntelligenceReportError):
        ArchitectureReportSection(
            ReportSectionType.OVERVIEW,
            "",
            "Summary",
            (),
        )


def test_section_model_rejects_invalid_findings():
    with pytest.raises(ArchitectureIntelligenceReportError):
        ArchitectureReportSection(
            ReportSectionType.OVERVIEW,
            "Title",
            "Summary",
            ("valid", ""),
        )


def test_report_model_rejects_empty_title():
    with pytest.raises(ArchitectureIntelligenceReportError):
        ArchitectureIntelligenceReport(
            "",
            0,
            0,
            0,
            (),
            (),
            "report",
        )


def test_report_model_rejects_invalid_sections():
    with pytest.raises(ArchitectureIntelligenceReportError):
        ArchitectureIntelligenceReport(
            "Report",
            0,
            0,
            0,
            ("invalid",),
            (),
            "report",
        )


def test_report_model_rejects_invalid_recommendations():
    with pytest.raises(ArchitectureIntelligenceReportError):
        ArchitectureIntelligenceReport(
            "Report",
            0,
            0,
            0,
            (),
            ("",),
            "report",
        )


def test_report_model_rejects_empty_report_text():
    with pytest.raises(ArchitectureIntelligenceReportError):
        ArchitectureIntelligenceReport(
            "Report",
            0,
            0,
            0,
            (),
            (),
            "",
        )


def test_report_is_incomplete_when_files_are_skipped(service):
    result = service.generate(
        investigation_result(
            total_files=3,
            analyzed_files=2,
            skipped_files=1,
        )
    )

    assert not result.is_complete


def test_report_is_complete_when_no_files_are_skipped(service):
    result = service.generate(investigation_result())

    assert result.is_complete
