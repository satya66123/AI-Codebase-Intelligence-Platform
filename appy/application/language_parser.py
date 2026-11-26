
from abc import ABC, abstractmethod
from dataclasses import dataclass
import ast

class LanguageParserError(ValueError):
    """Raised when source-code parsing fails."""

@dataclass(frozen=True)
class ParsedSource:
    """Represents the result of parsing a source file."""

    language: str
    filename: str
    tree: ast.AST
    line_count: int

class BaseLanguageParser(ABC):
    """Common interface for programming-language parsers."""

    @property
    @abstractmethod
    def language(self) -> str:
        """Return the language supported by this parser."""
        raise NotImplementedError

    @abstractmethod
    def parse(
        self,
        source_code: str,
        filename: str = "<unknown>",
    ) -> ParsedSource:
        """Parse source code and return its parsed representation."""
        raise NotImplementedError