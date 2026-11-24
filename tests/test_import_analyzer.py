
import pytest

from app.application.import_analyzer import (
    ImportAnalyzer,
    ImportAnalyzerError,
    ImportRecord,
)
from app.application.python_language_parser import (
    PythonLanguageParser,
)


@pytest.fixture
def analyzer():
    return ImportAnalyzer()


@pytest.fixture
def parser():
    return PythonLanguageParser()


def test_analyze_returns_import_records(analyzer, parser):
    result = analyzer.analyze(
        parser.parse("import os", "app.py")
    )

    assert isinstance(result, tuple)
    assert isinstance(result[0], ImportRecord)


def test_extract_regular_import(analyzer, parser):
    result = analyzer.analyze(parser.parse("import os", "app.py"))

    record = result[0]

    assert record.module == "os"
    assert record.imported_name is None
    assert record.import_type == "import"
    assert record.level == 0
    assert record.filename == "app.py"


def test_extract_multiple_imports(analyzer, parser):
    result = analyzer.analyze(
        parser.parse("import os, sys", "app.py")
    )

    assert len(result) == 2
    assert {record.module for record in result} == {"os", "sys"}


def test_extract_aliased_import(analyzer, parser):
    result = analyzer.analyze(
        parser.parse("import numpy as np")
    )

    assert result[0].module == "numpy"
    assert result[0].alias == "np"


def test_extract_from_import(analyzer, parser):
    result = analyzer.analyze(
        parser.parse("from pathlib import Path")
    )

    record = result[0]

    assert record.module == "pathlib"
    assert record.imported_name == "Path"
    assert record.import_type == "from_import"


def test_extract_multiple_from_import_names(analyzer, parser):
    result = analyzer.analyze(
        parser.parse("from os.path import join, exists")
    )

    assert len(result) == 2
    assert {record.imported_name for record in result} == {
        "join",
        "exists",
    }


def test_extract_from_import_alias(analyzer, parser):
    result = analyzer.analyze(
        parser.parse("from pathlib import Path as FilePath")
    )

    assert result[0].imported_name == "Path"
    assert result[0].alias == "FilePath"


def test_extract_relative_import(analyzer, parser):
    result = analyzer.analyze(
        parser.parse("from .utils import helper")
    )

    record = result[0]

    assert record.module == "utils"
    assert record.imported_name == "helper"
    assert record.level == 1
    assert record.is_relative is True


def test_extract_parent_relative_import(analyzer, parser):
    result = analyzer.analyze(
        parser.parse("from ..services import UserService")
    )

    record = result[0]

    assert record.module == "services"
    assert record.level == 2
    assert record.is_relative is True


def test_extract_star_import(analyzer, parser):
    result = analyzer.analyze(
        parser.parse("from helpers import *")
    )

    assert result[0].imported_name == "*"


def test_import_line_number(analyzer, parser):
    source = """
import os

from pathlib import Path
"""

    result = analyzer.analyze(parser.parse(source))

    assert result[0].line == 2
    assert result[1].line == 4


def test_nested_imports_are_detected(analyzer, parser):
    source = """
def load():
    import json
"""

    result = analyzer.analyze(parser.parse(source))

    assert len(result) == 1
    assert result[0].module == "json"
    assert result[0].line == 3


def test_no_imports_returns_empty_tuple(analyzer, parser):
    result = analyzer.analyze(
        parser.parse("value = 10")
    )

    assert result == ()


def test_reject_invalid_input(analyzer):
    with pytest.raises(
        ImportAnalyzerError,
        match="ParsedSource",
    ):
        analyzer.analyze("invalid input")
