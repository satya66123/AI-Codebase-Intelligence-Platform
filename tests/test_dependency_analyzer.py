
import pytest

from appy.application.dependency_analyzer import (
    DependencyAnalyzer,
    DependencyAnalyzerError,
    DependencyRecord,
)
from appy.application.import_analyzer import ImportAnalyzer
from appy.application.python_language_parser import PythonLanguageParser


@pytest.fixture
def analyzer():
    return DependencyAnalyzer()


@pytest.fixture
def import_analyzer():
    return ImportAnalyzer()


@pytest.fixture
def parser():
    return PythonLanguageParser()


def get_imports(parser, import_analyzer, source):
    parsed = parser.parse(source, "appy/services/user.py")
    return import_analyzer.analyze(parsed)


def test_analyze_returns_dependency_records(
    analyzer, parser, import_analyzer
):
    imports = get_imports(parser, import_analyzer, "import os")

    result = analyzer.analyze(imports)

    assert isinstance(result, tuple)
    assert isinstance(result[0], DependencyRecord)


def test_classify_standard_library_import(
    analyzer, parser, import_analyzer
):
    imports = get_imports(parser, import_analyzer, "import os")

    result = analyzer.analyze(imports)

    assert result[0].dependency_type == "standard_library"


def test_classify_standard_library_submodule(
    analyzer, parser, import_analyzer
):
    imports = get_imports(
        parser,
        import_analyzer,
        "from pathlib import Path",
    )

    result = analyzer.analyze(imports)

    assert result[0].dependency_type == "standard_library"


def test_classify_external_package(
    analyzer, parser, import_analyzer
):
    imports = get_imports(
        parser,
        import_analyzer,
        "import requests",
    )

    result = analyzer.analyze(imports)

    assert result[0].dependency_type == "external"


def test_classify_internal_module(
    analyzer, parser, import_analyzer
):
    imports = get_imports(
        parser,
        import_analyzer,
        "from appy.services import user",
    )

    result = analyzer.analyze(
        imports,
        internal_modules=["appy.services.user"],
    )

    assert result[0].dependency_type == "internal"


def test_classify_internal_submodule(
    analyzer, parser, import_analyzer
):
    imports = get_imports(
        parser,
        import_analyzer,
        "import appy.services.user",
    )

    result = analyzer.analyze(
        imports,
        internal_modules=["appy.services"],
    )

    assert result[0].dependency_type == "internal"


def test_classify_internal_module_from_path(
    analyzer, parser, import_analyzer
):
    imports = get_imports(
        parser,
        import_analyzer,
        "import appy.services.user",
    )

    result = analyzer.analyze(
        imports,
        internal_modules=["appy/services/user.py"],
    )

    assert result[0].dependency_type == "internal"


def test_classify_parent_package_as_internal(
    analyzer, parser, import_analyzer
):
    imports = get_imports(
        parser,
        import_analyzer,
        "import appy",
    )

    result = analyzer.analyze(
        imports,
        internal_modules=["appy.services.user"],
    )

    assert result[0].dependency_type == "internal"


def test_relative_import_is_unresolved(
    analyzer, parser, import_analyzer
):
    imports = get_imports(
        parser,
        import_analyzer,
        "from .utils import helper",
    )

    result = analyzer.analyze(
        imports,
        internal_modules=["appy.services.utils"],
    )

    assert result[0].dependency_type == "unresolved"
    assert result[0].is_relative is True


def test_preserve_dependency_metadata(
    analyzer, parser, import_analyzer
):
    imports = get_imports(
        parser,
        import_analyzer,
        "import requests as http",
    )

    result = analyzer.analyze(imports)

    record = result[0]

    assert record.source_file == "appy/services/user.py"
    assert record.imported_module == "requests"
    assert record.alias == "http"
    assert record.line == 1
    assert record.is_relative is False


def test_empty_imports(analyzer):
    assert analyzer.analyze([]) == ()


def test_reject_invalid_import_input(analyzer):
    with pytest.raises(
        DependencyAnalyzerError,
        match="iterable of ImportRecord",
    ):
        analyzer.analyze("import os")


def test_reject_invalid_import_record(analyzer):
    with pytest.raises(
        DependencyAnalyzerError,
        match="Every import must be an ImportRecord",
    ):
        analyzer.analyze([{"module": "os"}])


def test_reject_invalid_internal_modules(analyzer):
    with pytest.raises(
        DependencyAnalyzerError,
        match="iterable of module names",
    ):
        analyzer.analyze([], internal_modules="appy.services")


def test_reject_empty_internal_module_name(analyzer):
    with pytest.raises(
        DependencyAnalyzerError,
        match="non-empty strings",
    ):
        analyzer.analyze([], internal_modules=[""])
