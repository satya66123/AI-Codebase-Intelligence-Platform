
import json
from dataclasses import dataclass, fields, is_dataclass
from enum import Enum
from pathlib import Path
from collections.abc import Mapping

from appy.application.question_analysis_agent import (
    QuestionAnalysisResult,
)
from appy.application.repository_retrieval_service import (
    RepositoryRetrievalResult,
)
from appy.application.relevant_file_retrieval_service import (
    RelevantFileRetrievalResult,
)
from appy.application.relevant_code_retrieval_service import (
    RelevantCodeRetrievalResult,
)
from appy.application.dependency_context_service import (
    DependencyContextResult,
)
from appy.application.architecture_context_service import (
    ArchitectureContextResult,
)


class ContextBuilderError(ValueError):
    """Raised when intelligence context construction fails."""


@dataclass(frozen=True)
class ContextSection:
    """Represents one section of the assembled intelligence context."""

    name: str
    content: str
    source_files: tuple = ()
    entity_ids: tuple = ()

    def __post_init__(self):
        if not isinstance(self.name, str) or not self.name.strip():
            raise ContextBuilderError(
                "Context section name must be a non-empty string."
            )

        if not isinstance(self.content, str):
            raise ContextBuilderError(
                "Context section content must be a string."
            )

        if not isinstance(self.source_files, tuple):
            raise ContextBuilderError(
                "Context section source files must be a tuple."
            )

        if not isinstance(self.entity_ids, tuple):
            raise ContextBuilderError(
                "Context section entity IDs must be a tuple."
            )

        if not all(
            isinstance(item, str) and item.strip()
            for item in self.source_files
        ):
            raise ContextBuilderError(
                "Context section source files must contain non-empty strings."
            )

        if not all(
            isinstance(item, str) and item.strip()
            for item in self.entity_ids
        ):
            raise ContextBuilderError(
                "Context section entity IDs must contain non-empty strings."
            )


@dataclass(frozen=True)
class ContextBuildResult:
    """Contains the complete structured context for AI reasoning."""

    question: str
    intent: str
    sections: tuple
    context_text: str
    source_files: tuple
    entity_ids: tuple
    character_count: int
    max_characters: int
    truncated: bool

    def __post_init__(self):
        if not isinstance(self.question, str) or not self.question.strip():
            raise ContextBuilderError(
                "Question must be a non-empty string."
            )

        if not isinstance(self.intent, str) or not self.intent.strip():
            raise ContextBuilderError(
                "Intent must be a non-empty string."
            )

        if not isinstance(self.sections, tuple):
            raise ContextBuilderError(
                "Context sections must be a tuple."
            )

        if not all(
            isinstance(section, ContextSection)
            for section in self.sections
        ):
            raise ContextBuilderError(
                "Every section must be a ContextSection."
            )

        if not isinstance(self.context_text, str):
            raise ContextBuilderError(
                "Context text must be a string."
            )

        if not isinstance(self.source_files, tuple):
            raise ContextBuilderError(
                "Source files must be a tuple."
            )

        if not isinstance(self.entity_ids, tuple):
            raise ContextBuilderError(
                "Entity IDs must be a tuple."
            )

        if (
            not isinstance(self.character_count, int)
            or isinstance(self.character_count, bool)
            or self.character_count < 0
        ):
            raise ContextBuilderError(
                "Character count must be a non-negative integer."
            )

        if (
            not isinstance(self.max_characters, int)
            or isinstance(self.max_characters, bool)
            or self.max_characters <= 0
        ):
            raise ContextBuilderError(
                "Maximum characters must be a positive integer."
            )

        if self.character_count != len(self.context_text):
            raise ContextBuilderError(
                "Character count must match context text length."
            )

        if self.character_count > self.max_characters:
            raise ContextBuilderError(
                "Context text exceeds the maximum character limit."
            )

        if not isinstance(self.truncated, bool):
            raise ContextBuilderError(
                "Truncated must be a boolean."
            )


class ContextBuilder:
    """Combine repository intelligence into AI-ready context."""

    def build_context(
        self,
        question_analysis,
        repository_result,
        relevant_files,
        relevant_code,
        dependency_context,
        architecture_context,
        max_characters=12000,
    ):
        """Build a structured, source-aware context for AI reasoning."""

        self._validate_inputs(
            question_analysis,
            repository_result,
            relevant_files,
            relevant_code,
            dependency_context,
            architecture_context,
        )

        self._validate_max_characters(max_characters)

        try:
            sections = self._create_sections(
                repository_result,
                relevant_files,
                relevant_code,
                dependency_context,
                architecture_context,
            )

            sections = self._deduplicate_sections(sections)

            source_files = self._collect_source_files(sections)
            entity_ids = self._collect_entity_ids(sections)

            context_text, final_sections, truncated = (
                self._apply_character_limit(
                    sections,
                    max_characters,
                )
            )

            return ContextBuildResult(
                question=question_analysis.question,
                intent=self._intent_value(question_analysis.intent),
                sections=final_sections,
                context_text=context_text,
                source_files=source_files,
                entity_ids=entity_ids,
                character_count=len(context_text),
                max_characters=max_characters,
                truncated=truncated,
            )

        except ContextBuilderError:
            raise
        except Exception as exc:
            raise ContextBuilderError(
                "Unable to build intelligence context."
            ) from exc

    def _create_sections(
        self,
        repository_result,
        relevant_files,
        relevant_code,
        dependency_context,
        architecture_context,
    ):
        sections = []

        sections.append(
            self._create_section(
                name="repository_intelligence",
                value=repository_result,
            )
        )

        file_names = tuple(
            item.filename for item in relevant_files.files
        )

        sections.append(
            self._create_section(
                name="relevant_files",
                value=relevant_files,
                source_files=file_names,
            )
        )

        code_entities = relevant_code.code_entities

        sections.append(
            self._create_section(
                name="relevant_code",
                value=relevant_code,
                source_files=tuple(
                    entry.filename for entry in code_entities
                ),
                entity_ids=tuple(
                    entry.entity_id for entry in code_entities
                ),
            )
        )

        dependency_files = tuple(
            dependency.source_file
            for dependency in dependency_context.dependencies
        )

        sections.append(
            self._create_section(
                name="dependency_context",
                value=dependency_context,
                source_files=dependency_files,
            )
        )

        architecture_files = tuple(
            [graph.filename for graph in architecture_context.call_graphs]
            + [
                analysis.filename
                for analysis in architecture_context.inheritance_analyses
            ]
        )

        sections.append(
            self._create_section(
                name="architecture_context",
                value=architecture_context,
                source_files=architecture_files,
            )
        )

        return tuple(sections)

    @classmethod
    def _create_section(
        cls,
        name,
        value,
        source_files=(),
        entity_ids=(),
    ):
        content = json.dumps(
            cls._to_serializable(value),
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
        )

        return ContextSection(
            name=name,
            content=content,
            source_files=cls._unique_strings(source_files),
            entity_ids=cls._unique_strings(entity_ids),
        )

    @staticmethod
    def _to_serializable(value):
        """Convert supported Python values into JSON-compatible values."""

        if isinstance(value, Enum):
            return value.value

        if isinstance(value, Path):
            return str(value)

        if is_dataclass(value) and not isinstance(value, type):
            return {
                field.name: ContextBuilder._to_serializable(
                    getattr(value, field.name)
                )
                for field in fields(value)
            }

        if isinstance(value, Mapping):
            return {
                str(key): ContextBuilder._to_serializable(item)
                for key, item in value.items()
            }

        if isinstance(value, (tuple, list, set, frozenset)):
            return [
                ContextBuilder._to_serializable(item)
                for item in value
            ]

        if isinstance(value, (str, int, float, bool)) or value is None:
            return value

        return str(value)

    @staticmethod
    def _deduplicate_sections(sections):
        """Remove duplicate sections while preserving their original order."""

        unique_sections = []
        seen = set()

        for section in sections:
            key = (section.name, section.content)

            if key in seen:
                continue

            seen.add(key)
            unique_sections.append(section)

        return tuple(unique_sections)

    @staticmethod
    def _unique_strings(values):
        result = []
        seen = set()

        for value in values:
            if value not in seen:
                seen.add(value)
                result.append(value)

        return tuple(result)

    @classmethod
    def _collect_source_files(cls, sections):
        return cls._unique_strings(
            filename
            for section in sections
            for filename in section.source_files
        )

    @classmethod
    def _collect_entity_ids(cls, sections):
        return cls._unique_strings(
            entity_id
            for section in sections
            for entity_id in section.entity_ids
        )

    @staticmethod
    def _render_sections(sections):
        parts = []

        for section in sections:
            parts.append(
                f"## {section.name}\n{section.content}"
            )

        return "\n\n".join(parts)

    @classmethod
    def _apply_character_limit(cls, sections, max_characters):
        """Apply a deterministic character limit without exceeding it."""

        selected = []
        truncated = False

        for section in sections:
            candidate = selected + [section]
            candidate_text = cls._render_sections(candidate)

            if len(candidate_text) <= max_characters:
                selected.append(section)
                continue

            remaining = (
                max_characters
                - len(cls._render_sections(selected))
                - (2 if selected else 0)
            )

            if remaining > len(f"## {section.name}\n"):
                prefix = f"## {section.name}\n"
                available = remaining - len(prefix)

                shortened_content = section.content[:available]

                selected.append(
                    ContextSection(
                        name=section.name,
                        content=shortened_content,
                        source_files=section.source_files,
                        entity_ids=section.entity_ids,
                    )
                )

            truncated = True
            break

        final_text = cls._render_sections(selected)

        if len(final_text) > max_characters:
            final_text = final_text[:max_characters]
            truncated = True

        return final_text, tuple(selected), truncated

    @staticmethod
    def _intent_value(intent):
        if isinstance(intent, Enum):
            return str(intent.value)

        return str(intent)

    @staticmethod
    def _validate_max_characters(max_characters):
        if (
            not isinstance(max_characters, int)
            or isinstance(max_characters, bool)
            or max_characters <= 0
        ):
            raise ContextBuilderError(
                "Maximum characters must be a positive integer."
            )

    @staticmethod
    def _validate_inputs(
        question_analysis,
        repository_result,
        relevant_files,
        relevant_code,
        dependency_context,
        architecture_context,
    ):
        expected_types = (
            (question_analysis, QuestionAnalysisResult, "Question analysis"),
            (repository_result, RepositoryRetrievalResult, "Repository retrieval"),
            (relevant_files, RelevantFileRetrievalResult, "Relevant files"),
            (relevant_code, RelevantCodeRetrievalResult, "Relevant code"),
            (dependency_context, DependencyContextResult, "Dependency context"),
            (architecture_context, ArchitectureContextResult, "Architecture context"),
        )

        for value, expected_type, label in expected_types:
            if not isinstance(value, expected_type):
                raise ContextBuilderError(
                    f"{label} must be a {expected_type.__name__} instance."
                )

        if question_analysis.question != repository_result.question:
            raise ContextBuilderError(
                "Question analysis and repository retrieval questions must match."
            )

        if question_analysis.question != relevant_files.question:
            raise ContextBuilderError(
                "Question analysis and relevant file questions must match."
            )

        if question_analysis.question != relevant_code.question:
            raise ContextBuilderError(
                "Question analysis and relevant code questions must match."
            )
