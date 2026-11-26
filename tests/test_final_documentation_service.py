
"""Tests for the final documentation service."""

from datetime import timezone

import pytest

from appy.application.final_documentation_service import (
    DocumentationResult,
    DocumentationSection,
    FinalDocumentationError,
    FinalDocumentationService,
)


@pytest.fixture
def service():
    return FinalDocumentationService()


@pytest.fixture
def project_info():
    return {
        "project_name": "AI Codebase Intelligence Platform",
        "description": "An AI-powered platform for understanding codebases.",
        "version": "1.0.0",
        "status": "Development",
        "architecture": "Layered application architecture.",
        "technology_stack": ["Python", "Streamlit", "PyTest"],
    }


def test_generate_returns_documentation_result(service, project_info):
    result = service.generate(project_info)
    assert isinstance(result, DocumentationResult)


def test_generate_uses_project_name(service, project_info):
    result = service.generate(project_info)
    assert result.project_name == project_info["project_name"]


def test_generate_uses_markdown_format(service, project_info):
    result = service.generate(project_info)
    assert result.format == "markdown"


def test_generate_creates_markdown_heading(service, project_info):
    result = service.generate(project_info)
    assert result.content.startswith("# AI Codebase Intelligence Platform")


def test_generate_includes_project_description(service, project_info):
    result = service.generate(project_info)
    assert project_info["description"] in result.content


def test_generate_includes_version(service, project_info):
    result = service.generate(project_info)
    assert "**Version:** 1.0.0" in result.content


def test_generate_includes_status(service, project_info):
    result = service.generate(project_info)
    assert "**Status:** Development" in result.content


def test_generate_includes_architecture(service, project_info):
    result = service.generate(project_info)
    assert "Layered application architecture." in result.content


def test_generate_includes_technology_stack(service, project_info):
    result = service.generate(project_info)

    for technology in project_info["technology_stack"]:
        assert f"- {technology}" in result.content


def test_generate_omits_optional_sections_when_not_supplied(service):
    result = service.generate({
        "project_name": "Sample Project",
        "description": "A sample project.",
    })

    assert "## Architecture" not in result.content
    assert "## Technology Stack" not in result.content
    assert "## Testing and Validation" not in result.content
    assert "## Release Information" not in result.content


def test_generate_includes_development_phases(service, project_info):
    phases = [
        {"name": "Phase 0", "status": "Completed"},
        {"name": "Phase 1", "status": "Completed"},
    ]

    result = service.generate(project_info, phases=phases)

    assert "## Development Phases" in result.content
    assert "**Phase 0** — Completed" in result.content
    assert "**Phase 1** — Completed" in result.content


def test_generate_includes_phase_details(service, project_info):
    phases = [{
        "name": "Phase 4",
        "status": "In progress",
        "details": "Advanced code intelligence.",
    }]

    result = service.generate(project_info, phases=phases)
    assert "Advanced code intelligence." in result.content


def test_generate_includes_components(service, project_info):
    components = [{
        "name": "Repository Scanner",
        "description": "Discovers repository files.",
    }]

    result = service.generate(project_info, components=components)

    assert "## Implemented Components" in result.content
    assert "**Repository Scanner**" in result.content
    assert "Discovers repository files." in result.content


def test_generate_includes_component_status(service, project_info):
    components = [{
        "name": "Analysis Service",
        "description": "Analyzes source code.",
        "status": "Completed",
    }]

    result = service.generate(project_info, components=components)
    assert "Status: Completed" in result.content


def test_generate_includes_test_summary(service, project_info):
    test_summary = {
        "tests_passed": 59,
        "tests_failed": 0,
        "pass_rate": "100%",
    }

    result = service.generate(project_info, test_summary=test_summary)

    assert "## Testing and Validation" in result.content
    assert "- **Tests passed:** 59" in result.content
    assert "- **Tests failed:** 0" in result.content
    assert "- **Pass rate:** 100%" in result.content


def test_generate_formats_boolean_test_summary(service, project_info):
    result = service.generate(
        project_info,
        test_summary={"all_tests_passed": True},
    )

    assert "- **All tests passed:** Yes" in result.content


def test_generate_includes_release_information(service, project_info):
    result = service.generate(
        project_info,
        release_info={
            "release_version": "1.0.0",
            "release_ready": True,
        },
    )

    assert "## Release Information" in result.content
    assert "- **Release version:** 1.0.0" in result.content
    assert "- **Release ready:** Yes" in result.content


def test_generate_includes_custom_sections(service, project_info):
    result = service.generate(
        project_info,
        sections={
            "Security": "Security validation is documented.",
            "Deployment": "Deployment instructions are documented.",
        },
    )

    assert "## Security" in result.content
    assert "Security validation is documented." in result.content
    assert "## Deployment" in result.content


def test_generate_preserves_custom_section_order(service, project_info):
    result = service.generate(
        project_info,
        sections={
            "First Custom Section": "First content.",
            "Second Custom Section": "Second content.",
        },
    )

    first = result.content.index("## First Custom Section")
    second = result.content.index("## Second Custom Section")

    assert first < second


def test_generate_returns_sections(service, project_info):
    result = service.generate(project_info)

    assert isinstance(result.sections, tuple)
    assert result.section_count >= 1
    assert all(
        isinstance(section, DocumentationSection)
        for section in result.sections
    )


def test_generate_calculates_word_count(service, project_info):
    result = service.generate(project_info)
    assert result.word_count == len(result.content.split())


def test_generate_sets_timezone_aware_timestamp(service, project_info):
    result = service.generate(project_info)

    assert result.generated_at.tzinfo is not None
    assert result.generated_at.utcoffset() == timezone.utc.utcoffset(
        result.generated_at
    )


def test_result_filename_uses_project_name(service, project_info):
    result = service.generate(project_info)

    assert result.filename == (
        "ai-codebase-intelligence-platform-documentation.md"
    )


def test_result_filename_handles_special_characters(service):
    result = service.generate({
        "project_name": "AI / Codebase: Platform!",
        "description": "A sample project.",
    })

    assert result.filename == "ai-codebase-platform-documentation.md"


def test_result_is_complete(service, project_info):
    result = service.generate(project_info)
    assert result.is_complete is True


@pytest.mark.parametrize(
    "project_info",
    [None, [], (), "project", 123],
)
def test_generate_rejects_non_mapping_project_info(service, project_info):
    with pytest.raises(FinalDocumentationError) as exc_info:
        service.generate(project_info)

    assert exc_info.value.stage == "input_validation"


@pytest.mark.parametrize(
    "project_info",
    [
        {},
        {"description": "Description only."},
        {"project_name": "Project only"},
        {"project_name": "", "description": "Description."},
        {"project_name": "Project", "description": " "},
    ],
)
def test_generate_rejects_missing_required_project_fields(
    service,
    project_info,
):
    with pytest.raises(FinalDocumentationError) as exc_info:
        service.generate(project_info)

    assert exc_info.value.stage == "input_validation"


def test_generate_rejects_invalid_version(service):
    with pytest.raises(FinalDocumentationError):
        service.generate({
            "project_name": "Project",
            "description": "Description.",
            "version": " ",
        })


def test_generate_rejects_invalid_status(service):
    with pytest.raises(FinalDocumentationError):
        service.generate({
            "project_name": "Project",
            "description": "Description.",
            "status": "",
        })


def test_generate_rejects_invalid_architecture(service):
    with pytest.raises(FinalDocumentationError):
        service.generate({
            "project_name": "Project",
            "description": "Description.",
            "architecture": " ",
        })


@pytest.mark.parametrize("stack", ["Python", 123, [None], [" "]])
def test_generate_rejects_invalid_technology_stack(service, stack):
    with pytest.raises(FinalDocumentationError):
        service.generate({
            "project_name": "Project",
            "description": "Description.",
            "technology_stack": stack,
        })


@pytest.mark.parametrize("phases", ["Phase 1", {}, [None], [123]])
def test_generate_rejects_invalid_phases(service, phases):
    with pytest.raises(FinalDocumentationError):
        service.generate(
            {
                "project_name": "Project",
                "description": "Description.",
            },
            phases=phases,
        )


def test_generate_rejects_phase_without_name(service):
    with pytest.raises(FinalDocumentationError) as exc_info:
        service.generate(
            {
                "project_name": "Project",
                "description": "Description.",
            },
            phases=[{"status": "Completed"}],
        )

    assert exc_info.value.stage == "phase_validation"


def test_generate_rejects_phase_without_status(service):
    with pytest.raises(FinalDocumentationError):
        service.generate(
            {
                "project_name": "Project",
                "description": "Description.",
            },
            phases=[{"name": "Phase 1"}],
        )


def test_generate_rejects_empty_phase_details(service):
    with pytest.raises(FinalDocumentationError):
        service.generate(
            {
                "project_name": "Project",
                "description": "Description.",
            },
            phases=[{
                "name": "Phase 1",
                "status": "Completed",
                "details": " ",
            }],
        )


@pytest.mark.parametrize("components", ["component", {}, [None], [123]])
def test_generate_rejects_invalid_components(service, components):
    with pytest.raises(FinalDocumentationError):
        service.generate(
            {
                "project_name": "Project",
                "description": "Description.",
            },
            components=components,
        )


def test_generate_rejects_component_without_name(service):
    with pytest.raises(FinalDocumentationError):
        service.generate(
            {
                "project_name": "Project",
                "description": "Description.",
            },
            components=[{"description": "Description."}],
        )


def test_generate_rejects_component_without_description(service):
    with pytest.raises(FinalDocumentationError):
        service.generate(
            {
                "project_name": "Project",
                "description": "Description.",
            },
            components=[{"name": "Component"}],
        )


def test_generate_rejects_invalid_component_status(service):
    with pytest.raises(FinalDocumentationError):
        service.generate(
            {
                "project_name": "Project",
                "description": "Description.",
            },
            components=[{
                "name": "Component",
                "description": "Description.",
                "status": " ",
            }],
        )


def test_generate_rejects_invalid_test_summary_type(service):
    with pytest.raises(FinalDocumentationError):
        service.generate(
            {
                "project_name": "Project",
                "description": "Description.",
            },
            test_summary=[],
        )


def test_generate_rejects_unsupported_test_summary_value(service):
    with pytest.raises(FinalDocumentationError):
        service.generate(
            {
                "project_name": "Project",
                "description": "Description.",
            },
            test_summary={"details": ["not supported"]},
        )


def test_generate_rejects_invalid_release_info_type(service):
    with pytest.raises(FinalDocumentationError):
        service.generate(
            {
                "project_name": "Project",
                "description": "Description.",
            },
            release_info=[],
        )


def test_generate_rejects_unsupported_release_value(service):
    with pytest.raises(FinalDocumentationError):
        service.generate(
            {
                "project_name": "Project",
                "description": "Description.",
            },
            release_info={"links": ["not supported"]},
        )


def test_generate_rejects_empty_custom_section_title(service):
    with pytest.raises(FinalDocumentationError) as exc_info:
        service.generate(
            {
                "project_name": "Project",
                "description": "Description.",
            },
            sections={" ": "Content."},
        )

    assert exc_info.value.stage == "section_validation"


def test_generate_rejects_empty_custom_section_content(service):
    with pytest.raises(FinalDocumentationError):
        service.generate(
            {
                "project_name": "Project",
                "description": "Description.",
            },
            sections={"Security": " "},
        )


def test_documentation_section_rejects_empty_title():
    with pytest.raises(ValueError):
        DocumentationSection(title=" ", content="Content.")


def test_documentation_section_rejects_empty_content():
    with pytest.raises(ValueError):
        DocumentationSection(title="Title", content=" ")


def test_generated_document_ends_with_newline(service, project_info):
    result = service.generate(project_info)
    assert result.content.endswith("\n")


def test_generate_supports_empty_optional_collections(service, project_info):
    result = service.generate(
        project_info,
        sections={},
        components=[],
        phases=[],
        test_summary={},
        release_info={},
    )

    assert result.is_complete is True
    assert "No test summary details were supplied." in result.content
    assert "No release information was supplied." in result.content
