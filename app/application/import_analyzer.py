
import ast
from dataclasses import dataclass

from app.application.language_parser import ParsedSource


class ImportAnalyzerError(ValueError):
    """Raised when import analysis fails."""


@dataclass(frozen=True)
class ImportRecord:
    """Represents an import statement or imported name."""

    module: str | None
    imported_name: str | None
    alias: str | None
    import_type: str
    level: int
    line: int
    filename: str

    @property
    def is_relative(self) -> bool:
        return self.level > 0


class ImportAnalyzer:
    """Extract detailed import information from Python AST."""

    def analyze(self, parsed_source: ParsedSource) -> tuple:
        """Analyze imports in a parsed Python source file."""

        if not isinstance(parsed_source, ParsedSource):
            raise ImportAnalyzerError(
                "Input must be a ParsedSource instance."
            )

        if not isinstance(parsed_source.tree, ast.Module):
            raise ImportAnalyzerError(
                "Python source must contain an AST module."
            )

        records = []

        for node in ast.walk(parsed_source.tree):
            if isinstance(node, ast.Import):
                records.extend(
                    self._analyze_import(node, parsed_source.filename)
                )

            elif isinstance(node, ast.ImportFrom):
                records.extend(
                    self._analyze_from_import(
                        node,
                        parsed_source.filename,
                    )
                )

        records.sort(key=lambda record: (record.line, record.import_type))

        return tuple(records)

    @staticmethod
    def _analyze_import(
        node: ast.Import,
        filename: str,
    ) -> list:
        """Analyze regular import statements."""

        return [
            ImportRecord(
                module=alias.name,
                imported_name=None,
                alias=alias.asname,
                import_type="import",
                level=0,
                line=node.lineno,
                filename=filename,
            )
            for alias in node.names
        ]

    @staticmethod
    def _analyze_from_import(
        node: ast.ImportFrom,
        filename: str,
    ) -> list:
        """Analyze from-import statements, including relative imports."""

        return [
            ImportRecord(
                module=node.module,
                imported_name=alias.name,
                alias=alias.asname,
                import_type="from_import",
                level=node.level,
                line=node.lineno,
                filename=filename,
            )
            for alias in node.names
        ]
