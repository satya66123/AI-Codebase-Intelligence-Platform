
import ast
from dataclasses import dataclass
from pathlib import Path

from appy.application.language_parser import ParsedSource


class CodeEntityExtractionError(ValueError):
    """Raised when code entity extraction fails."""


@dataclass(frozen=True)
class CodeEntity:
    """Represents a structured code entity."""

    name: str
    entity_type: str
    qualified_name: str
    filename: str
    line: int
    end_line: int | None
    parent: str | None
    docstring: str | None


class CodeEntityExtractor:
    """Extract modules, classes, functions, and methods from Python AST."""

    def extract(self, parsed_source: ParsedSource) -> tuple:
        """Extract code entities from a parsed source file."""

        if not isinstance(parsed_source, ParsedSource):
            raise CodeEntityExtractionError(
                "Input must be a ParsedSource instance."
            )

        if not isinstance(parsed_source.tree, ast.Module):
            raise CodeEntityExtractionError(
                "Python source must contain an AST module."
            )

        filename = parsed_source.filename
        module_name = self._get_module_name(filename)

        entities = [
            CodeEntity(
                name=module_name,
                entity_type="module",
                qualified_name=module_name,
                filename=filename,
                line=1,
                end_line=parsed_source.line_count or None,
                parent=None,
                docstring=ast.get_docstring(parsed_source.tree),
            )
        ]

        self._extract_nested_entities(
            body=parsed_source.tree.body,
            filename=filename,
            parent_name=module_name,
            parent_type="module",
            entities=entities,
        )

        return tuple(entities)

    @staticmethod
    def _get_module_name(filename: str) -> str:
        """Derive a module name from its filename."""

        if filename == "<unknown>":
            return "<module>"

        return Path(filename).stem or "<module>"

    def _extract_nested_entities(
        self,
        body,
        filename,
        parent_name,
        parent_type,
        entities,
    ):
        """Recursively extract classes and functions."""

        for node in body:
            if isinstance(node, ast.ClassDef):
                entity_type = "class"

            elif isinstance(
                node,
                (ast.FunctionDef, ast.AsyncFunctionDef),
            ):
                entity_type = (
                    "method"
                    if parent_type == "class"
                    else "function"
                )

            else:
                continue

            qualified_name = f"{parent_name}.{node.name}"

            entity = CodeEntity(
                name=node.name,
                entity_type=entity_type,
                qualified_name=qualified_name,
                filename=filename,
                line=node.lineno,
                end_line=getattr(node, "end_lineno", None),
                parent=parent_name,
                docstring=ast.get_docstring(node),
            )

            entities.append(entity)

            self._extract_nested_entities(
                body=node.body,
                filename=filename,
                parent_name=qualified_name,
                parent_type=entity_type,
                entities=entities,
            )
