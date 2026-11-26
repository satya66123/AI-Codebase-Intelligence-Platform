
import pytest

from appy.application.ast_analyzer import (
    ASTAnalyzer,
    ASTAnalyzerError,
    ASTAnalysisResult,
)
from appy.application.python_language_parser import (
    PythonLanguageParser,
)


@pytest.fixture
def analyzer():
    return ASTAnalyzer()


@pytest.fixture
def parser():
    return PythonLanguageParser()


def test_analyze_returns_result(analyzer, parser):
    parsed = parser.parse("value = 10")

    result = analyzer.analyze(parsed)

    assert isinstance(result, ASTAnalysisResult)


def test_analyze_preserves_file_metadata(analyzer, parser):
    parsed = parser.parse(
        "value = 10",
        "example.py",
    )

    result = analyzer.analyze(parsed)

    assert result.filename == "example.py"
    assert result.language == "Python"


def test_extract_function(analyzer, parser):
    parsed = parser.parse(
        "def greet():\n    return 'Hello'"
    )

    result = analyzer.analyze(parsed)

    assert len(result.functions) == 1
    assert result.functions[0]["name"] == "greet"
    assert result.functions[0]["line"] == 1
    assert result.functions[0]["type"] == "function"


def test_extract_async_function(analyzer, parser):
    parsed = parser.parse(
        "async def fetch():\n    return None"
    )

    result = analyzer.analyze(parsed)

    assert result.functions[0]["name"] == "fetch"
    assert result.functions[0]["type"] == "async"


def test_extract_class(analyzer, parser):
    parsed = parser.parse(
        "class Employee:\n    pass"
    )

    result = analyzer.analyze(parsed)

    assert len(result.classes) == 1
    assert result.classes[0]["name"] == "Employee"
    assert result.classes[0]["line"] == 1


def test_extract_imports(analyzer, parser):
    source = """
import os
from pathlib import Path
"""

    result = analyzer.analyze(parser.parse(source))

    assert len(result.imports) == 2
    assert result.imports[0]["module"] == "os"
    assert result.imports[0]["type"] == "import"
    assert result.imports[1]["module"] == "pathlib"
    assert result.imports[1]["name"] == "Path"


def test_extract_aliased_import(analyzer, parser):
    parsed = parser.parse("import numpy as np")

    result = analyzer.analyze(parsed)

    assert result.imports[0]["module"] == "numpy"
    assert result.imports[0]["alias"] == "np"


def test_extract_variable_assignment(analyzer, parser):
    parsed = parser.parse(
        "total = 100\nname = 'Alex'"
    )

    result = analyzer.analyze(parsed)

    variable_names = {
        item["name"]
        for item in result.variables
    }

    assert "total" in variable_names
    assert "name" in variable_names


def test_extract_annotated_assignment(analyzer, parser):
    parsed = parser.parse("age: int = 25")

    result = analyzer.analyze(parsed)

    assert result.variables[0]["name"] == "age"


def test_count_return_statements(analyzer, parser):
    source = """
def first():
    return 1

def second():
    return 2
"""

    result = analyzer.analyze(parser.parse(source))

    assert result.return_count == 2


def test_count_ast_nodes(analyzer, parser):
    parsed = parser.parse("value = 10")

    result = analyzer.analyze(parsed)

    assert result.total_nodes > 0


def test_empty_source(analyzer, parser):
    result = analyzer.analyze(parser.parse(""))

    assert result.functions == ()
    assert result.classes == ()
    assert result.imports == ()
    assert result.variables == ()
    assert result.return_count == 0


def test_reject_invalid_input(analyzer):
    with pytest.raises(
        ASTAnalyzerError,
        match="ParsedSource",
    ):
        analyzer.analyze("not parsed source")
