
import pytest

from appy.application.code_entity_extractor import (
    CodeEntity,
    CodeEntityExtractionError,
    CodeEntityExtractor,
)
from appy.application.python_language_parser import (
    PythonLanguageParser,
)


@pytest.fixture
def extractor():
    return CodeEntityExtractor()


@pytest.fixture
def parser():
    return PythonLanguageParser()


def test_extract_returns_code_entities(extractor, parser):
    parsed = parser.parse("value = 10", "example.py")

    result = extractor.extract(parsed)

    assert isinstance(result, tuple)
    assert all(isinstance(item, CodeEntity) for item in result)


def test_extract_module_entity(extractor, parser):
    result = extractor.extract(
        parser.parse("value = 10", "example.py")
    )

    module = result[0]

    assert module.name == "example"
    assert module.entity_type == "module"
    assert module.qualified_name == "example"
    assert module.parent is None


def test_extract_module_from_unknown_filename(extractor, parser):
    result = extractor.extract(parser.parse("value = 10"))

    assert result[0].name == "<module>"


def test_extract_function(extractor, parser):
    source = "def greet():\n    return 'Hello'"

    result = extractor.extract(parser.parse(source, "appy.py"))

    function = next(
        entity for entity in result
        if entity.name == "greet"
    )

    assert function.entity_type == "function"
    assert function.qualified_name == "appy.greet"
    assert function.parent == "appy"
    assert function.line == 1


def test_extract_class(extractor, parser):
    source = "class Employee:\n    pass"

    result = extractor.extract(parser.parse(source, "models.py"))

    class_entity = next(
        entity for entity in result
        if entity.name == "Employee"
    )

    assert class_entity.entity_type == "class"
    assert class_entity.qualified_name == "models.Employee"
    assert class_entity.parent == "models"


def test_extract_method(extractor, parser):
    source = """
class Employee:
    def work(self):
        pass
"""

    result = extractor.extract(parser.parse(source, "models.py"))

    method = next(
        entity for entity in result
        if entity.name == "work"
    )

    assert method.entity_type == "method"
    assert method.qualified_name == "models.Employee.work"
    assert method.parent == "models.Employee"


def test_extract_async_function(extractor, parser):
    source = "async def fetch():\n    pass"

    result = extractor.extract(parser.parse(source))

    function = next(
        entity for entity in result
        if entity.name == "fetch"
    )

    assert function.entity_type == "function"


def test_extract_nested_function(extractor, parser):
    source = """
def outer():
    def inner():
        pass
"""

    result = extractor.extract(parser.parse(source, "appy.py"))

    inner = next(
        entity for entity in result
        if entity.name == "inner"
    )

    assert inner.entity_type == "function"
    assert inner.parent == "appy.outer"
    assert inner.qualified_name == "appy.outer.inner"


def test_extract_docstrings(extractor, parser):
    source = '''
"""Module documentation."""

def greet():
    """Function documentation."""
    pass
'''

    result = extractor.extract(parser.parse(source, "appy.py"))

    module = result[0]
    function = next(
        entity for entity in result
        if entity.name == "greet"
    )

    assert module.docstring == "Module documentation."
    assert function.docstring == "Function documentation."


def test_extract_source_line_information(extractor, parser):
    source = """
class Example:
    def run(self):
        return True
"""

    result = extractor.extract(parser.parse(source, "example.py"))

    class_entity = next(
        entity for entity in result
        if entity.name == "Example"
    )

    method = next(
        entity for entity in result
        if entity.name == "run"
    )

    assert class_entity.line == 2
    assert class_entity.end_line == 4
    assert method.line == 3
    assert method.end_line == 4


def test_empty_source_returns_module_entity(extractor, parser):
    result = extractor.extract(parser.parse("", "empty.py"))

    assert len(result) == 1
    assert result[0].entity_type == "module"


def test_reject_invalid_input(extractor):
    with pytest.raises(
        CodeEntityExtractionError,
        match="ParsedSource",
    ):
        extractor.extract("invalid input")
