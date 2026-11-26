
"""Generate structured Markdown documentation for the application."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import PurePosixPath
from typing import Any


class FinalDocumentationError(ValueError):
    """Raised when documentation generation or validation fails."""

    def __init__(self, message: str, stage: str = "documentation") -> None:
        super().__init__(message)
        self.stage = stage


@dataclass(frozen=True)
class DocumentationSection:
    """One section in the generated project documentation."""

    title: str
    content: str

    def __post_init__(self) -> None:
        if not isinstance(self.title, str) or not self.title.strip():
            raise ValueError("Documentation section title must be non-empty.")

        if not isinstance(self.content, str) or not self.content.strip():
            raise ValueError("Documentation section content must be non-empty.")


@dataclass(frozen=True)
class DocumentationResult:
    """Immutable generated documentation artifact."""

    project_name: str
    format: str
    content: str
    sections: tuple[DocumentationSection, ...]
    generated_at: datetime
    word_count: int

    @property
    def section_count(self) -> int:
        return len(self.sections)

    @property
    def is_complete(self) -> bool:
        return bool(self.project_name and self.content and self.sections)

    @property
    def filename(self) -> str:
        slug = "".join(
            character.lower() if character.isalnum() else "-"
            for character in self.project_name
        )
        slug = "-".join(part for part in slug.split("-") if part)
        return f"{slug or 'project'}-documentation.md"


class FinalDocumentationService:
    """Build validated Markdown documentation from supplied project details."""

    REQUIRED_PROJECT_FIELDS = ("project_name", "description")
    DEFAULT_SECTIONS = (
        "Project Overview",
        "Architecture",
        "Technology Stack",
        "Development Phases",
        "Implemented Components",
        "Testing and Validation",
        "Release Information",
    )

    def generate(
        self,
        project_info: Mapping[str, Any],
        sections: Mapping[str, str] | None = None,
        components: Sequence[Mapping[str, Any]] | None = None,
        phases: Sequence[Mapping[str, Any]] | None = None,
        test_summary: Mapping[str, Any] | None = None,
        release_info: Mapping[str, Any] | None = None,
    ) -> DocumentationResult:
        """Generate a complete Markdown project document."""

        self._validate_project_info(project_info)
        self._validate_optional_mapping("test_summary", test_summary)
        self._validate_optional_mapping("release_info", release_info)
        self._validate_optional_sequence("components", components)
        self._validate_optional_sequence("phases", phases)

        project_name = project_info["project_name"].strip()
        document_sections: list[DocumentationSection] = []

        overview = self._build_overview(project_info)
        document_sections.append(
            DocumentationSection("Project Overview", overview)
        )

        architecture = self._build_architecture(project_info)
        if architecture:
            document_sections.append(
                DocumentationSection("Architecture", architecture)
            )

        technology_stack = self._build_technology_stack(project_info)
        if technology_stack:
            document_sections.append(
                DocumentationSection("Technology Stack", technology_stack)
            )

        phase_content = self._build_phases(phases)
        if phase_content:
            document_sections.append(
                DocumentationSection("Development Phases", phase_content)
            )

        component_content = self._build_components(components)
        if component_content:
            document_sections.append(
                DocumentationSection("Implemented Components", component_content)
            )

        if test_summary is not None:
            document_sections.append(
                DocumentationSection(
                    "Testing and Validation",
                    self._build_test_summary(test_summary),
                )
            )

        if release_info is not None:
            document_sections.append(
                DocumentationSection(
                    "Release Information",
                    self._build_release_info(release_info),
                )
            )

        if sections is not None:
            for title, content in sections.items():
                self._validate_section(title, content)
                document_sections.append(
                    DocumentationSection(title.strip(), content.strip())
                )

        content = self._render_markdown(project_name, document_sections)
        generated_at = datetime.now(timezone.utc)

        return DocumentationResult(
            project_name=project_name,
            format="markdown",
            content=content,
            sections=tuple(document_sections),
            generated_at=generated_at,
            word_count=len(content.split()),
        )

    @staticmethod
    def _validate_project_info(project_info: Mapping[str, Any]) -> None:
        if not isinstance(project_info, Mapping):
            raise FinalDocumentationError(
                "project_info must be a mapping.",
                stage="input_validation",
            )

        for field in FinalDocumentationService.REQUIRED_PROJECT_FIELDS:
            value = project_info.get(field)
            if not isinstance(value, str) or not value.strip():
                raise FinalDocumentationError(
                    f"project_info requires a non-empty '{field}' field.",
                    stage="input_validation",
                )

    @staticmethod
    def _validate_optional_mapping(
        name: str,
        value: Mapping[str, Any] | None,
    ) -> None:
        if value is not None and not isinstance(value, Mapping):
            raise FinalDocumentationError(
                f"{name} must be a mapping or None.",
                stage="input_validation",
            )

    @staticmethod
    def _validate_optional_sequence(
        name: str,
        value: Sequence[Mapping[str, Any]] | None,
    ) -> None:
        if value is None:
            return

        if (
            not isinstance(value, (list, tuple))
            or isinstance(value, (str, bytes))
        ):
            raise FinalDocumentationError(
                f"{name} must be a list, tuple, or None.",
                stage="input_validation",
            )

        for index, item in enumerate(value):
            if not isinstance(item, Mapping):
                raise FinalDocumentationError(
                    f"{name}[{index}] must be a mapping.",
                    stage="input_validation",
                )

    @staticmethod
    def _validate_section(title: Any, content: Any) -> None:
        if not isinstance(title, str) or not title.strip():
            raise FinalDocumentationError(
                "Custom section titles must be non-empty strings.",
                stage="section_validation",
            )

        if not isinstance(content, str) or not content.strip():
            raise FinalDocumentationError(
                f"Custom section '{title}' must contain text.",
                stage="section_validation",
            )

    @staticmethod
    def _build_overview(project_info: Mapping[str, Any]) -> str:
        description = project_info["description"].strip()
        lines = [description]

        version = project_info.get("version")
        if version is not None:
            if not isinstance(version, str) or not version.strip():
                raise FinalDocumentationError(
                    "Project version must be a non-empty string when supplied.",
                    stage="input_validation",
                )
            lines.append(f"**Version:** {version.strip()}")

        status = project_info.get("status")
        if status is not None:
            if not isinstance(status, str) or not status.strip():
                raise FinalDocumentationError(
                    "Project status must be a non-empty string when supplied.",
                    stage="input_validation",
                )
            lines.append(f"**Status:** {status.strip()}")

        return "\n\n".join(lines)

    @staticmethod
    def _build_architecture(project_info: Mapping[str, Any]) -> str:
        architecture = project_info.get("architecture")
        if architecture is None:
            return ""

        if not isinstance(architecture, str) or not architecture.strip():
            raise FinalDocumentationError(
                "Architecture must be a non-empty string when supplied.",
                stage="input_validation",
            )

        return architecture.strip()

    @staticmethod
    def _build_technology_stack(project_info: Mapping[str, Any]) -> str:
        technologies = project_info.get("technology_stack")
        if technologies is None:
            return ""

        if not isinstance(technologies, (list, tuple)):
            raise FinalDocumentationError(
                "technology_stack must be a list or tuple.",
                stage="input_validation",
            )

        normalized = []
        for technology in technologies:
            if not isinstance(technology, str) or not technology.strip():
                raise FinalDocumentationError(
                    "Technology stack entries must be non-empty strings.",
                    stage="input_validation",
                )
            normalized.append(technology.strip())

        if not normalized:
            return ""

        return "\n".join(f"- {technology}" for technology in normalized)

    @staticmethod
    def _build_phases(
        phases: Sequence[Mapping[str, Any]] | None,
    ) -> str:
        if not phases:
            return ""

        lines: list[str] = []

        for index, phase in enumerate(phases):
            name = phase.get("name")
            status = phase.get("status")

            if not isinstance(name, str) or not name.strip():
                raise FinalDocumentationError(
                    f"Phase entry {index} requires a non-empty name.",
                    stage="phase_validation",
                )

            if not isinstance(status, str) or not status.strip():
                raise FinalDocumentationError(
                    f"Phase '{name}' requires a non-empty status.",
                    stage="phase_validation",
                )

            line = f"- **{name.strip()}** — {status.strip()}"

            details = phase.get("details")
            if details is not None:
                if not isinstance(details, str) or not details.strip():
                    raise FinalDocumentationError(
                        f"Phase '{name}' details must be non-empty text.",
                        stage="phase_validation",
                    )
                line += f": {details.strip()}"

            lines.append(line)

        return "\n".join(lines)

    @staticmethod
    def _build_components(
        components: Sequence[Mapping[str, Any]] | None,
    ) -> str:
        if not components:
            return ""

        lines: list[str] = []

        for index, component in enumerate(components):
            name = component.get("name")
            description = component.get("description")

            if not isinstance(name, str) or not name.strip():
                raise FinalDocumentationError(
                    f"Component entry {index} requires a non-empty name.",
                    stage="component_validation",
                )

            if not isinstance(description, str) or not description.strip():
                raise FinalDocumentationError(
                    f"Component '{name}' requires a non-empty description.",
                    stage="component_validation",
                )

            line = f"- **{name.strip()}**: {description.strip()}"

            status = component.get("status")
            if status is not None:
                if not isinstance(status, str) or not status.strip():
                    raise FinalDocumentationError(
                        f"Component '{name}' status must be non-empty text.",
                        stage="component_validation",
                    )
                line += f" (Status: {status.strip()})"

            lines.append(line)

        return "\n".join(lines)

    @staticmethod
    def _build_test_summary(test_summary: Mapping[str, Any]) -> str:
        lines: list[str] = []

        for key, value in test_summary.items():
            label = str(key).replace("_", " ").strip().capitalize()

            if isinstance(value, bool):
                rendered = "Yes" if value else "No"
            elif isinstance(value, (str, int, float)):
                rendered = str(value)
            else:
                raise FinalDocumentationError(
                    f"Unsupported test summary value for '{key}'.",
                    stage="test_summary_validation",
                )

            lines.append(f"- **{label}:** {rendered}")

        if not lines:
            return "No test summary details were supplied."

        return "\n".join(lines)

    @staticmethod
    def _build_release_info(release_info: Mapping[str, Any]) -> str:
        lines: list[str] = []

        for key, value in release_info.items():
            if not isinstance(value, (str, int, float, bool)):
                raise FinalDocumentationError(
                    f"Unsupported release information value for '{key}'.",
                    stage="release_validation",
                )

            label = str(key).replace("_", " ").strip().capitalize()
            rendered = "Yes" if value is True else "No" if value is False else str(value)
            lines.append(f"- **{label}:** {rendered}")

        if not lines:
            return "No release information was supplied."

        return "\n".join(lines)

    @staticmethod
    def _render_markdown(
        project_name: str,
        sections: Sequence[DocumentationSection],
    ) -> str:
        parts = [f"# {project_name}"]

        for section in sections:
            parts.append(f"## {section.title}\n\n{section.content}")

        return "\n\n".join(parts).strip() + "\n"
