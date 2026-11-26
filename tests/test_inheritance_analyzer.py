
import pytest

from appy.application.inheritance_analyzer import (
    InheritanceAnalyzer,
    InheritanceAnalyzerError,
    InheritanceAnalysisResult,
    InheritanceRecord,
)
from appy.application.python_language_parser import (
    PythonLanguageParser,
)


@pytest.fixture
def analyzer():
    return InheritanceAnalyzer()


@pytest.fixture
def parser():
    return PythonLanguageParser()


def test_analyze_returns_result(analyzer, parser):
    parsed = parser.parse(
        "class Child(Parent):\n    pass",
        "models.py",
    )

    result = analyzer.analyze(parsed)

    assert isinstance(result, InheritanceAnalysisResult)


def test_extract_direct_inheritance(analyzer, parser):
    source = """
class Animal:
    pass

class Dog(Animal):
    pass
"""

    result = analyzer.analyze(parser.parse(source, "models.py"))

    assert result.total_relationships == 1

    relationship = result.relationships[0]

    assert isinstance(relationship, InheritanceRecord)
    assert relationship.class_name == "Dog"
    assert relationship.base_class == "Animal"
    assert relationship.inheritance_type == "single"


def test_extract_multiple_inheritance(analyzer, parser):
    source = """
class Flyer:
    pass

class Swimmer:
    pass

class Duck(Flyer, Swimmer):
    pass
"""

    result = analyzer.analyze(parser.parse(source))

    duck_relationships = [
        item
        for item in result.relationships
        if item.class_name == "Duck"
    ]

    assert len(duck_relationships) == 2
    assert {
        item.base_class
        for item in duck_relationships
    } == {"Flyer", "Swimmer"}

    assert all(
        item.inheritance_type == "multiple"
        for item in duck_relationships
    )


def test_extract_qualified_base_class(analyzer, parser):
    source = """
class Child(models.BaseModel):
    pass
"""

    result = analyzer.analyze(parser.parse(source))

    assert result.relationships[0].base_class == "models.BaseModel"


def test_extract_generic_base_class(analyzer, parser):
    source = """
class Repository(BaseRepository[User]):
    pass
"""

    result = analyzer.analyze(parser.parse(source))

    assert result.relationships[0].base_class == "BaseRepository"


def test_extract_class_without_bases(analyzer, parser):
    source = """
class Employee:
    pass
"""

    result = analyzer.analyze(parser.parse(source, "models.py"))

    assert result.classes_without_bases == ("models.Employee",)
    assert result.total_relationships == 0


def test_extract_multiple_classes(analyzer, parser):
    source = """
class A(BaseA):
    pass

class B(BaseB):
    pass
"""

    result = analyzer.analyze(parser.parse(source))

    assert result.total_relationships == 2


def test_extract_inheritance_line_number(analyzer, parser):
    source = """
class Parent:
    pass

class Child(Parent):
    pass
"""

    result = analyzer.analyze(parser.parse(source))

    assert result.relationships[0].line == 5


def test_preserve_filename(analyzer, parser):
    result = analyzer.analyze(
        parser.parse(
            "class Child(Parent):\n    pass",
            "models.py",
        )
    )

    assert result.relationships[0].filename == "models.py"


def test_extract_nested_class_inheritance(analyzer, parser):
    source = """
class Outer:
    class Inner(Base):
        pass
"""

    result = analyzer.analyze(parser.parse(source, "models.py"))

    relationship = result.relationships[0]

    assert relationship.class_name == "Inner"
    assert relationship.qualified_class_name == "models.Outer.Inner"
    assert relationship.base_class == "Base"


def test_extract_class_inside_function(analyzer, parser):
    source = """
def create():
    class Local(Base):
        pass
"""

    result = analyzer.analyze(parser.parse(source, "models.py"))

    relationship = result.relationships[0]

    assert relationship.qualified_class_name == "models.create.Local"


def test_empty_source(analyzer, parser):
    result = analyzer.analyze(parser.parse(""))

    assert result.relationships == ()
    assert result.classes_without_bases == ()
    assert result.total_relationships == 0


def test_reject_invalid_input(analyzer):
    with pytest.raises(
        InheritanceAnalyzerError,
        match="ParsedSource",
    ):
        analyzer.analyze("invalid input")
