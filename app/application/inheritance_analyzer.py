
import ast
from dataclasses import dataclass
from pathlib import Path

from app.application.language_parser import ParsedSource


class InheritanceAnalyzerError(ValueError):
    """Raised when inheritance analysis fails."""


@dataclass(frozen=True)
class InheritanceRecord:
    """Represents a class inheritance relationship."""

    filename: str
    class_name: str
    qualified_class_name: str
    base_class: str
    line: int
    inheritance_type: str


@dataclass(frozen=True)
class InheritanceAnalysisResult:
    """Contains inheritance relationships discovered in a source file."""

    filename: str
    relationships: tuple
    classes_without_bases: tuple
    total_relationships: int


class InheritanceAnalyzer:
    """Extract class inheritance relationships from Python AST."""

    def analyze(
        self,
        parsed_source: ParsedSource,
    ) -> InheritanceAnalysisResult:
        """Analyze inheritance relationships in a parsed Python file."""

        if not isinstance(parsed_source, ParsedSource):
            raise InheritanceAnalyzerError(
                "Input must be a ParsedSource instance."
            )

        if not isinstance(parsed_source.tree, ast.Module):
            raise InheritanceAnalyzerError(
                "Python source must contain an AST module."
            )

        relationships = []
        classes_without_bases = []

        module_name = (
            "<module>"
            if parsed_source.filename == "<unknown>"
            else Path(parsed_source.filename).stem
        )

        self._extract_classes(
            body=parsed_source.tree.body,
            filename=parsed_source.filename,
            parent_name=module_name,
            relationships=relationships,
            classes_without_bases=classes_without_bases,
        )

        return InheritanceAnalysisResult(
            filename=parsed_source.filename,
            relationships=tuple(relationships),
            classes_without_bases=tuple(classes_without_bases),
            total_relationships=len(relationships),
        )

    def _extract_classes(
        self,
        body,
        filename,
        parent_name,
        relationships,
        classes_without_bases,
    ):
        """Recursively inspect class definitions."""

        for node in body:
            if isinstance(node, ast.ClassDef):
                qualified_name = f"{parent_name}.{node.name}"

                if not node.bases:
                    classes_without_bases.append(qualified_name)

                for base in node.bases:
                    base_name = self._resolve_base_name(base)

                    relationships.append(
                        InheritanceRecord(
                            filename=filename,
                            class_name=node.name,
                            qualified_class_name=qualified_name,
                            base_class=base_name,
                            line=node.lineno,
                            inheritance_type=(
                                "multiple"
                                if len(node.bases) > 1
                                else "single"
                            ),
                        )
                    )

                self._extract_classes(
                    body=node.body,
                    filename=filename,
                    parent_name=qualified_name,
                    relationships=relationships,
                    classes_without_bases=classes_without_bases,
                )

            elif isinstance(
                node,
                (ast.FunctionDef, ast.AsyncFunctionDef),
            ):
                # Classes nested inside functions are also discovered.
                self._extract_classes(
                    body=node.body,
                    filename=filename,
                    parent_name=f"{parent_name}.{node.name}",
                    relationships=relationships,
                    classes_without_bases=classes_without_bases,
                )

    @classmethod
    def _resolve_base_name(cls, node):
        """Resolve simple and qualified base-class expressions."""

        if isinstance(node, ast.Name):
            return node.id

        if isinstance(node, ast.Attribute):
            parent = cls._resolve_base_name(node.value)
            return f"{parent}.{node.attr}"

        if isinstance(node, ast.Subscript):
            return cls._resolve_base_name(node.value)

        if isinstance(node, ast.Call):
            return cls._resolve_base_name(node.func)

        return "<dynamic>"
