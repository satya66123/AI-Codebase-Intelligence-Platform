
import pytest

from app.application.dependency_analyzer import (
    DependencyAnalyzer,
    DependencyRecord,
)
from app.application.dependency_context_service import (
    DependencyContextError,
    DependencyContextResult,
    DependencyContextService,
)
from app.application.import_analyzer import ImportRecord


@pytest.fixture
def imports():
    return (
        ImportRecord(
            module="app.auth",
            imported_name=None,
            alias=None,
            import_type="import",
            level=0,
            line=1,
            filename="app/service.py",
        ),
        ImportRecord(
            module="os",
            imported_name=None,
            alias=None,
            import_type="import",
            level=0,
            line=2,
            filename="app/service.py",
        ),
        ImportRecord(
            module="requests",
            imported_name=None,
            alias=None,
            import_type="import",
            level=0,
            line=3,
            filename="app/service.py",
        ),
        ImportRecord(
            module=None,
            imported_name="helper",
            alias=None,
            import_type="from_import",
            level=1,
            line=4,
            filename="app/utils.py",
        ),
        ImportRecord(
            module="app.database",
            imported_name="connect",
            alias="db_connect",
            import_type="from_import",
            level=0,
            line=5,
            filename="app/database_service.py",
        ),
    )


@pytest.fixture
def service():
    return DependencyContextService()


@pytest.fixture
def internal_modules():
    return (
        "app",
        "app.auth",
        "app.database",
    )


# ---------------------------------------------------------
# Initialization tests
# ---------------------------------------------------------


def test_service_initialization():
    service = DependencyContextService()

    assert service is not None


def test_service_uses_default_dependency_analyzer():
    service = DependencyContextService()

    assert isinstance(
        service.dependency_analyzer,
        DependencyAnalyzer,
    )


def test_service_accepts_custom_dependency_analyzer():
    analyzer = DependencyAnalyzer()

    service = DependencyContextService(
        dependency_analyzer=analyzer,
    )

    assert service.dependency_analyzer is analyzer


def test_service_rejects_invalid_dependency_analyzer():
    with pytest.raises(DependencyContextError):
        DependencyContextService(
            dependency_analyzer="invalid",
        )


# ---------------------------------------------------------
# Result model tests
# ---------------------------------------------------------


def test_result_creation():
    result = DependencyContextResult(
        total_dependencies=0,
        dependencies=(),
        dependencies_by_file={},
        dependency_counts={},
    )

    assert result.total_dependencies == 0
    assert result.dependencies == ()


def test_result_rejects_negative_total():
    with pytest.raises(DependencyContextError):
        DependencyContextResult(
            total_dependencies=-1,
            dependencies=(),
            dependencies_by_file={},
            dependency_counts={},
        )


def test_result_rejects_boolean_total():
    with pytest.raises(DependencyContextError):
        DependencyContextResult(
            total_dependencies=True,
            dependencies=(),
            dependencies_by_file={},
            dependency_counts={},
        )


def test_result_rejects_non_tuple_dependencies():
    with pytest.raises(DependencyContextError):
        DependencyContextResult(
            total_dependencies=0,
            dependencies=[],
            dependencies_by_file={},
            dependency_counts={},
        )


def test_result_rejects_total_mismatch():
    with pytest.raises(DependencyContextError):
        DependencyContextResult(
            total_dependencies=1,
            dependencies=(),
            dependencies_by_file={},
            dependency_counts={},
        )


def test_result_rejects_invalid_dependency():
    with pytest.raises(DependencyContextError):
        DependencyContextResult(
            total_dependencies=1,
            dependencies=("invalid",),
            dependencies_by_file={},
            dependency_counts={},
        )


def test_result_rejects_invalid_dependencies_by_file():
    with pytest.raises(DependencyContextError):
        DependencyContextResult(
            total_dependencies=0,
            dependencies=(),
            dependencies_by_file=(),
            dependency_counts={},
        )


def test_result_rejects_invalid_dependency_counts():
    with pytest.raises(DependencyContextError):
        DependencyContextResult(
            total_dependencies=0,
            dependencies=(),
            dependencies_by_file={},
            dependency_counts=(),
        )


# ---------------------------------------------------------
# Dependency classification tests
# ---------------------------------------------------------


def test_retrieve_returns_dependency_context(
    service,
    imports,
    internal_modules,
):
    result = service.retrieve(
        imports,
        internal_modules,
    )

    assert isinstance(result, DependencyContextResult)


def test_retrieve_classifies_internal_dependency(
    service,
    imports,
    internal_modules,
):
    result = service.retrieve(
        imports,
        internal_modules,
    )

    internal = [
        item
        for item in result.dependencies
        if item.imported_module == "app.auth"
    ]

    assert len(internal) == 1
    assert internal[0].dependency_type == "internal"


def test_retrieve_classifies_standard_library_dependency(
    service,
    imports,
    internal_modules,
):
    result = service.retrieve(
        imports,
        internal_modules,
    )

    standard_library = [
        item
        for item in result.dependencies
        if item.imported_module == "os"
    ]

    assert len(standard_library) == 1
    assert standard_library[0].dependency_type == "standard_library"


def test_retrieve_classifies_external_dependency(
    service,
    imports,
    internal_modules,
):
    result = service.retrieve(
        imports,
        internal_modules,
    )

    external = [
        item
        for item in result.dependencies
        if item.imported_module == "requests"
    ]

    assert len(external) == 1
    assert external[0].dependency_type == "external"


def test_retrieve_classifies_relative_import_as_unresolved(
    service,
    imports,
    internal_modules,
):
    result = service.retrieve(
        imports,
        internal_modules,
    )

    unresolved = [
        item
        for item in result.dependencies
        if item.source_file == "app/utils.py"
    ]

    assert len(unresolved) == 1
    assert unresolved[0].dependency_type == "unresolved"


def test_retrieve_preserves_import_metadata(
    service,
    imports,
    internal_modules,
):
    result = service.retrieve(
        imports,
        internal_modules,
    )

    database_dependency = next(
        item
        for item in result.dependencies
        if item.imported_module == "app.database"
    )

    assert database_dependency.imported_name == "connect"
    assert database_dependency.alias == "db_connect"
    assert database_dependency.line == 5
    assert database_dependency.source_file == "app/database_service.py"


# ---------------------------------------------------------
# Dependency grouping tests
# ---------------------------------------------------------


def test_retrieve_groups_dependencies_by_file(
    service,
    imports,
    internal_modules,
):
    result = service.retrieve(
        imports,
        internal_modules,
    )

    assert "app/service.py" in result.dependencies_by_file
    assert "app/utils.py" in result.dependencies_by_file
    assert "app/database_service.py" in result.dependencies_by_file


def test_retrieve_groups_correct_number_of_dependencies(
    service,
    imports,
    internal_modules,
):
    result = service.retrieve(
        imports,
        internal_modules,
    )

    assert len(result.dependencies_by_file["app/service.py"]) == 3


def test_retrieve_grouped_records_match_flat_records(
    service,
    imports,
    internal_modules,
):
    result = service.retrieve(
        imports,
        internal_modules,
    )

    grouped = tuple(
        dependency
        for records in result.dependencies_by_file.values()
        for dependency in records
    )

    assert set(grouped) == set(result.dependencies)


def test_retrieve_sorts_file_groups(
    service,
    imports,
    internal_modules,
):
    result = service.retrieve(
        imports,
        internal_modules,
    )

    filenames = tuple(result.dependencies_by_file)

    assert filenames == tuple(sorted(filenames))


# ---------------------------------------------------------
# Dependency count tests
# ---------------------------------------------------------


def test_retrieve_reports_total_dependencies(
    service,
    imports,
    internal_modules,
):
    result = service.retrieve(
        imports,
        internal_modules,
    )

    assert result.total_dependencies == 5


def test_retrieve_reports_internal_count(
    service,
    imports,
    internal_modules,
):
    result = service.retrieve(
        imports,
        internal_modules,
    )

    assert result.dependency_counts["internal"] == 2


def test_retrieve_reports_external_count(
    service,
    imports,
    internal_modules,
):
    result = service.retrieve(
        imports,
        internal_modules,
    )

    assert result.dependency_counts["external"] == 1


def test_retrieve_reports_standard_library_count(
    service,
    imports,
    internal_modules,
):
    result = service.retrieve(
        imports,
        internal_modules,
    )

    assert result.dependency_counts["standard_library"] == 1


def test_retrieve_reports_unresolved_count(
    service,
    imports,
    internal_modules,
):
    result = service.retrieve(
        imports,
        internal_modules,
    )

    assert result.dependency_counts["unresolved"] == 1


def test_dependency_counts_sum_to_total(
    service,
    imports,
    internal_modules,
):
    result = service.retrieve(
        imports,
        internal_modules,
    )

    assert sum(result.dependency_counts.values()) == (
        result.total_dependencies
    )


# ---------------------------------------------------------
# Relevant file filtering tests
# ---------------------------------------------------------


def test_retrieve_filters_relevant_files(
    service,
    imports,
    internal_modules,
):
    result = service.retrieve(
        imports,
        internal_modules,
        relevant_files=("app/service.py",),
    )

    assert result.total_dependencies == 3

    assert set(result.dependencies_by_file) == {
        "app/service.py",
    }


def test_retrieve_filters_multiple_relevant_files(
    service,
    imports,
    internal_modules,
):
    result = service.retrieve(
        imports,
        internal_modules,
        relevant_files=(
            "app/service.py",
            "app/utils.py",
        ),
    )

    assert result.total_dependencies == 4


def test_retrieve_returns_empty_when_no_files_match(
    service,
    imports,
    internal_modules,
):
    result = service.retrieve(
        imports,
        internal_modules,
        relevant_files=("app/missing.py",),
    )

    assert result.total_dependencies == 0
    assert result.dependencies == ()
    assert result.dependencies_by_file == {}


def test_retrieve_by_file(
    service,
    imports,
    internal_modules,
):
    result = service.retrieve_by_file(
        imports=imports,
        filename="app/utils.py",
        internal_modules=internal_modules,
    )

    assert result.total_dependencies == 1
    assert set(result.dependencies_by_file) == {
        "app/utils.py",
    }


def test_retrieve_by_file_rejects_empty_filename(
    service,
    imports,
):
    with pytest.raises(DependencyContextError):
        service.retrieve_by_file(
            imports=imports,
            filename="",
        )


# ---------------------------------------------------------
# Empty input tests
# ---------------------------------------------------------


def test_retrieve_accepts_empty_imports(service):
    result = service.retrieve(
        imports=(),
        internal_modules=(),
    )

    assert result.total_dependencies == 0
    assert result.dependencies == ()
    assert result.dependencies_by_file == {}


def test_retrieve_accepts_empty_internal_modules(
    service,
    imports,
):
    result = service.retrieve(
        imports=imports,
        internal_modules=(),
    )

    assert result.total_dependencies == len(imports)


def test_retrieve_accepts_empty_relevant_files(
    service,
    imports,
    internal_modules,
):
    result = service.retrieve(
        imports=imports,
        internal_modules=internal_modules,
        relevant_files=(),
    )

    assert result.total_dependencies == 0


# ---------------------------------------------------------
# Invalid input tests
# ---------------------------------------------------------


def test_retrieve_rejects_none_imports(service):
    with pytest.raises(DependencyContextError):
        service.retrieve(None)


def test_retrieve_rejects_string_imports(service):
    with pytest.raises(DependencyContextError):
        service.retrieve("invalid")


def test_retrieve_rejects_dictionary_imports(service):
    with pytest.raises(DependencyContextError):
        service.retrieve({"invalid": "value"})


def test_retrieve_rejects_non_iterable_imports(service):
    with pytest.raises(DependencyContextError):
        service.retrieve(123)


def test_retrieve_rejects_invalid_import_record(service):
    with pytest.raises(DependencyContextError):
        service.retrieve(("invalid",))


def test_retrieve_rejects_none_internal_modules(
    service,
    imports,
):
    with pytest.raises(DependencyContextError):
        service.retrieve(
            imports,
            internal_modules=None,
        )


def test_retrieve_rejects_string_internal_modules(
    service,
    imports,
):
    with pytest.raises(DependencyContextError):
        service.retrieve(
            imports,
            internal_modules="app",
        )


def test_retrieve_rejects_invalid_internal_module(
    service,
    imports,
):
    with pytest.raises(DependencyContextError):
        service.retrieve(
            imports,
            internal_modules=("app", ""),
        )


def test_retrieve_rejects_invalid_relevant_files(
    service,
    imports,
):
    with pytest.raises(DependencyContextError):
        service.retrieve(
            imports,
            relevant_files="app/service.py",
        )


def test_retrieve_rejects_invalid_relevant_filename(
    service,
    imports,
):
    with pytest.raises(DependencyContextError):
        service.retrieve(
            imports,
            relevant_files=("app/service.py", ""),
        )
