
from app.application.language_parser import (
    BaseLanguageParser,
    LanguageParserError,
)
from app.application.python_language_parser import (
    PythonLanguageParser,
)


class LanguageParserFactoryError(ValueError):
    """Raised when a suitable language parser cannot be found."""


class LanguageParserFactory:
    """Register and retrieve parsers for supported programming languages."""

    def __init__(self):
        self._parsers = {}

        # Register the initial supported language parser.
        self.register_parser(PythonLanguageParser())

    def register_parser(self, parser: BaseLanguageParser) -> None:
        """Register a language parser."""

        if not isinstance(parser, BaseLanguageParser):
            raise LanguageParserFactoryError(
                "Parser must implement BaseLanguageParser."
            )

        language = parser.language

        if not isinstance(language, str) or not language.strip():
            raise LanguageParserFactoryError(
                "Parser must provide a valid language name."
            )

        language_key = language.strip().casefold()

        if language_key in self._parsers:
            raise LanguageParserFactoryError(
                f"A parser for {language} is already registered."
            )

        self._parsers[language_key] = parser

    def get_parser(self, language: str) -> BaseLanguageParser:
        """Retrieve a parser using its language name."""

        if not isinstance(language, str) or not language.strip():
            raise LanguageParserFactoryError(
                "Language must be a non-empty string."
            )

        language_key = language.strip().casefold()

        parser = self._parsers.get(language_key)

        if parser is None:
            raise LanguageParserFactoryError(
                f"No parser registered for language: {language}"
            )

        return parser

    def get_supported_languages(self) -> tuple:
        """Return all registered language names."""

        return tuple(
            parser.language
            for parser in self._parsers.values()
        )
