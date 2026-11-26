
import ast

import pytest

from appy.application.language_parser import (
    BaseLanguageParser,
    ParsedSource,
)
from appy.application.language_parser_factory import (
    LanguageParserFactory,
    LanguageParserFactoryError,
)


class DummyJavaScriptParser(BaseLanguageParser):
    """Test parser used to verify factory extensibility."""

    @property
    def language(self):
        return "JavaScript"

    def parse(self, source_code, filename="<unknown>"):
        return ParsedSource(
            language=self.language,
            filename=filename,
            tree=ast.parse(""),
            line_count=0,
        )


@pytest.fixture
def factory():
    return LanguageParserFactory()


def test_factory_registers_python_parser(factory):
    assert "Python" in factory.get_supported_languages()


def test_factory_returns_python_parser(factory):
    parser = factory.get_parser("Python")

    assert parser.language == "Python"


def test_factory_language_lookup_is_case_insensitive(factory):
    parser = factory.get_parser("python")

    assert parser.language == "Python"


def test_factory_language_lookup_ignores_surrounding_spaces(factory):
    parser = factory.get_parser("  Python  ")

    assert parser.language == "Python"


def test_factory_rejects_unsupported_language(factory):
    with pytest.raises(
        LanguageParserFactoryError,
        match="No parser registered",
    ):
        factory.get_parser("Java")


def test_factory_rejects_empty_language(factory):
    with pytest.raises(
        LanguageParserFactoryError,
        match="non-empty string",
    ):
        factory.get_parser("")


def test_factory_rejects_invalid_parser(factory):
    with pytest.raises(
        LanguageParserFactoryError,
        match="BaseLanguageParser",
    ):
        factory.register_parser(object())


def test_factory_registers_additional_parser(factory):
    factory.register_parser(DummyJavaScriptParser())

    parser = factory.get_parser("JavaScript")

    assert parser.language == "JavaScript"


def test_factory_rejects_duplicate_parser(factory):
    from appy.application.python_language_parser import (
        PythonLanguageParser,
    )

    with pytest.raises(
        LanguageParserFactoryError,
        match="already registered",
    ):
        factory.register_parser(PythonLanguageParser())


def test_factory_returns_all_supported_languages(factory):
    factory.register_parser(DummyJavaScriptParser())

    languages = factory.get_supported_languages()

    assert "Python" in languages
    assert "JavaScript" in languages
    assert len(languages) == 2
