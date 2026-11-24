
import ast

from app.application.language_parser import (
    BaseLanguageParser,
    LanguageParserError,
    ParsedSource,
)

class PythonLanguageParser(BaseLanguageParser):
    """Parse Python source code using the built-in AST module."""

    @property
    def language(self) -> str:
        return "Python"

    def parse(
        self,
        source_code: str,
        filename: str = "<unknown>",
    ) -> ParsedSource:
        """Convert Python source code into an AST representation."""

        if not isinstance(source_code, str):
            raise LanguageParserError(
                "Source code must be a string."
            )

        if not isinstance(filename, str) or not filename.strip():
            raise LanguageParserError(
                "Filename must be a non-empty string."
            )

        try:
            syntax_tree = ast.parse(
                source_code,
                filename=filename,
                mode="exec",
                type_comments=True,
            )

        except SyntaxError as exc:
            raise LanguageParserError(
                f"Python syntax error in {filename} "
                f"at line {exc.lineno}: {exc.msg}"
            ) from exc

        return ParsedSource(
            language=self.language,
            filename=filename,
            tree=syntax_tree,
            line_count=len(source_code.splitlines()),
        )