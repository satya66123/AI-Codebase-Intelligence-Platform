
import ast

import pytest

from appy.application.language_parser import (
    BaseLanguageParser,
    LanguageParserError,
    ParsedSource,
)
from appy.application.python_language_parser import (
    PythonLanguageParser,
)

@pytest.fixture
def parser():
    return PythonLanguageParser()

def test_parser_implements_base_parser(parser):
    assert isinstance(parser, BaseLanguageParser)

def test_parser_language_name(parser):
    assert parser.language == "Python"

def test_parse_valid_python_code(parser):
    source = """
def greet():
    return "Hello"
"""

    result = parser.parse(source, "example.py")

    assert isinstance(result, ParsedSource)
    assert result.language == "Python"
    assert result.filename == "example.py"
    assert isinstance(result.tree, ast.Module)

def test_parse_function_definition(parser):
    source = "def calculate():\n    return 10"

    result = parser.parse(source)

    function_nodes = [
        node
        for node in ast.walk(result.tree)
        if isinstance(node, ast.FunctionDef)
    ]

    assert len(function_nodes) == 1
    assert function_nodes[0].name == "calculate"

def test_parse_class_definition(parser):
    source = """
class Employee:
    def work(self):
        pass
"""

    result = parser.parse(source)

    class_nodes = [
        node
        for node in ast.walk(result.tree)
        if isinstance(node, ast.ClassDef)
    ]

    assert len(class_nodes) == 1
    assert class_nodes[0].name == "Employee"

def test_parse_empty_source(parser):
    result = parser.parse("")

    assert isinstance(result.tree, ast.Module)
    assert result.line_count == 0
    assert result.tree.body == []

def test_line_count(parser):
    source = "x = 10\ny = 20\nz = 30"

    result = parser.parse(source)

    assert result.line_count == 3

def test_parse_invalid_python_code(parser):
    source = "def broken(\n"

    with pytest.raises(LanguageParserError, match="syntax error"):
        parser.parse(source, "broken.py")

def test_parse_non_string_source(parser):
    with pytest.raises(
        LanguageParserError,
        match="Source code must be a string",
    ):
        parser.parse(123)

def test_parse_invalid_filename(parser):
    with pytest.raises(
        LanguageParserError,
        match="Filename must be a non-empty string",
    ):
        parser.parse("x = 10", "")

def test_parse_preserves_filename(parser):
    result = parser.parse("value = 100", "services/example.py")

    assert result.filename == "services/example.py"