
import ast
from dataclasses import dataclass

from app.application.language_parser import ParsedSource


class ASTAnalyzerError(ValueError):
    """Raised when AST analysis fails."""


@dataclass(frozen=True)
class ASTAnalysisResult:
    """Contains a structured summary of an AST."""

    filename: str
    language: str
    total_nodes: int
    functions: tuple
    classes: tuple
    imports: tuple
    variables: tuple
    return_count: int


class ASTAnalyzer:
    """Analyze parsed source code using its Abstract Syntax Tree."""

    def analyze(self, parsed_source: ParsedSource) -> ASTAnalysisResult:
        """Analyze an existing parsed source representation."""

        if not isinstance(parsed_source, ParsedSource):
            raise ASTAnalyzerError(
                "Input must be a ParsedSource instance."
            )

        if not isinstance(parsed_source.tree, ast.AST):
            raise ASTAnalyzerError(
                "Parsed source must contain a valid AST."
            )

        try:
            tree = parsed_source.tree

            functions = self._extract_functions(tree)
            classes = self._extract_classes(tree)
            imports = self._extract_imports(tree)
            variables = self._extract_variables(tree)

            return ASTAnalysisResult(
                filename=parsed_source.filename,
                language=parsed_source.language,
                total_nodes=sum(1 for _ in ast.walk(tree)),
                functions=tuple(functions),
                classes=tuple(classes),
                imports=tuple(imports),
                variables=tuple(variables),
                return_count=sum(
                    1
                    for node in ast.walk(tree)
                    if isinstance(node, ast.Return)
                ),
            )

        except (AttributeError, TypeError) as exc:
            raise ASTAnalyzerError(
                "Unable to analyze the supplied AST."
            ) from exc

    @staticmethod
    def _extract_functions(tree):
        """Extract synchronous and asynchronous function definitions."""

        results = []

        for node in ast.walk(tree):
            if isinstance(
                node,
                (ast.FunctionDef, ast.AsyncFunctionDef),
            ):
                results.append({
                    "name": node.name,
                    "line": node.lineno,
                    "end_line": getattr(node, "end_lineno", None),
                    "type": (
                        "async"
                        if isinstance(node, ast.AsyncFunctionDef)
                        else "function"
                    ),
                })

        return results

    @staticmethod
    def _extract_classes(tree):
        """Extract class definitions."""

        results = []

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                results.append({
                    "name": node.name,
                    "line": node.lineno,
                    "end_line": getattr(node, "end_lineno", None),
                })

        return results

    @staticmethod
    def _extract_imports(tree):
        """Extract import and from-import statements."""

        results = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    results.append({
                        "module": alias.name,
                        "alias": alias.asname,
                        "line": node.lineno,
                        "type": "import",
                    })

            elif isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    results.append({
                        "module": node.module,
                        "name": alias.name,
                        "alias": alias.asname,
                        "level": node.level,
                        "line": node.lineno,
                        "type": "from_import",
                    })

        return results

    @staticmethod
    def _extract_variables(tree):
        """Extract variable assignment names."""

        results = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    for name in ast.walk(target):
                        if isinstance(name, ast.Name):
                            results.append({
                                "name": name.id,
                                "line": node.lineno,
                            })

            elif isinstance(node, ast.AnnAssign):
                for name in ast.walk(node.target):
                    if isinstance(name, ast.Name):
                        results.append({
                            "name": name.id,
                            "line": node.lineno,
                        })

        return results
