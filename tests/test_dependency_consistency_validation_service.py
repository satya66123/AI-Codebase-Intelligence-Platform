
"""Tests for dependency consistency validation."""

import pytest

from appy.application.dependency_analyzer import (
    DependencyAnalyzer,
    DependencyRecord,
)
from appy.application.dependency_consistency_validation_service import (
    DependencyConsistencyIssue,
    DependencyConsistencySeverity,
    DependencyConsistencyValidationError,
    DependencyConsistencyValidationResult,
    DependencyConsistencyValidationService,
)
from appy.application.import_analyzer import ImportRecord


@pytest.fixture
def service():
    return DependencyConsistencyValidationService()


def make_import(
    filename="src/main.py",
    module="os",
    imported_name=None,
    alias=None,
    import_type="import",
    level=0,
    line=1,
):
    return ImportRecord(
        module=module,
        imported_name=imported_name,
        alias=alias,
        import_type=import_type,
        level=level,
        line=line,
        filename=filename,
    )


def make_dependency(
    source_file="src/main.py",
    imported_module="os",
    imported_name=None,
    alias=None,
    dependency_type="standard_library",
    line=1,
    is_relative=False,
):
    return DependencyRecord(
        source_file=source_file,
        imported_module=imported_module,
        imported_name=imported_name,
        alias=alias,
        dependency_type=dependency_type,
        line=line,
        is_relative=is_relative,
    )


def test_empty_inputs_are_valid(service):
    result = service.validate([], [])

    assert result.is_valid is True
    assert result.imports_checked == 0
    assert result.dependencies_checked == 0
    assert result.matched_dependencies == 0
    assert result.total_issues == 0
    assert result.healthy is True


def test_matching_standard_library_dependency_is_valid(service):
    imports = [make_import(module="os")]
    dependencies = [make_dependency(imported_module="os")]

    result = service.validate(imports, dependencies)

    assert result.is_valid is True
    assert result.imports_checked == 1
    assert result.dependencies_checked == 1
    assert result.matched_dependencies == 1
    assert result.missing_dependencies == 0
    assert result.unexpected_dependencies == 0
    assert result.mismatched_classifications == 0


def test_matching_external_dependency_is_valid(service):
    imports = [make_import(module="requests")]
    dependencies = [
        make_dependency(
            imported_module="requests",
            dependency_type="external",
        )
    ]

    result = service.validate(imports, dependencies)

    assert result.is_valid is True
    assert result.matched_dependencies == 1


def test_matching_internal_dependency_is_valid(service):
    imports = [make_import(module="appy.services.user_service")]
    dependencies = [
        make_dependency(
            imported_module="appy.services.user_service",
            dependency_type="internal",
        )
    ]

    result = service.validate(
        imports,
        dependencies,
        internal_modules=["appy.services.user_service"],
    )

    assert result.is_valid is True
    assert result.matched_dependencies == 1


def test_relative_import_is_valid_when_unresolved(service):
    imports = [
        make_import(
            module="utils",
            imported_name="helper",
            import_type="from_import",
            level=1,
        )
    ]
    dependencies = [
        make_dependency(
            imported_module="utils",
            imported_name="helper",
            dependency_type="unresolved",
            is_relative=True,
        )
    ]

    result = service.validate(imports, dependencies)

    assert result.is_valid is True
    assert result.matched_dependencies == 1


def test_missing_dependency_is_reported(service):
    imports = [make_import(module="os")]
    result = service.validate(imports, [])

    assert result.is_valid is False
    assert result.missing_dependencies == 1
    assert result.unexpected_dependencies == 0
    assert result.error_count == 1
    assert result.issues[0].code == "MISSING_DEPENDENCY"
    assert result.issues[0].source_file == "src/main.py"
    assert result.issues[0].line == 1


def test_unexpected_dependency_is_reported(service):
    dependencies = [make_dependency(imported_module="os")]
    result = service.validate([], dependencies)

    assert result.is_valid is False
    assert result.unexpected_dependencies == 1
    assert result.missing_dependencies == 0
    assert result.issues[0].code == "UNEXPECTED_DEPENDENCY"


def test_classification_mismatch_is_reported(service):
    imports = [make_import(module="os")]
    dependencies = [
        make_dependency(
            imported_module="os",
            dependency_type="external",
        )
    ]

    result = service.validate(imports, dependencies)

    assert result.is_valid is False
    assert result.matched_dependencies == 1
    assert result.mismatched_classifications == 1
    assert any(
        issue.code == "CLASSIFICATION_MISMATCH"
        for issue in result.issues
    )


def test_wrong_source_file_is_reported_as_missing_and_unexpected(service):
    imports = [make_import(filename="src/main.py")]
    dependencies = [
        make_dependency(source_file="src/other.py")
    ]

    result = service.validate(imports, dependencies)

    assert result.is_valid is False
    assert result.missing_dependencies == 1
    assert result.unexpected_dependencies == 1
    assert {issue.code for issue in result.issues} == {
        "MISSING_DEPENDENCY",
        "UNEXPECTED_DEPENDENCY",
    }


def test_wrong_line_number_is_reported(service):
    imports = [make_import(line=5)]
    dependencies = [make_dependency(line=6)]

    result = service.validate(imports, dependencies)

    assert result.is_valid is False
    assert result.missing_dependencies == 1
    assert result.unexpected_dependencies == 1


def test_wrong_module_is_reported(service):
    imports = [make_import(module="os")]
    dependencies = [make_dependency(imported_module="sys")]

    result = service.validate(imports, dependencies)

    assert result.is_valid is False
    assert result.missing_dependencies == 1
    assert result.unexpected_dependencies == 1


def test_wrong_imported_name_is_reported(service):
    imports = [
        make_import(
            module="pathlib",
            imported_name="Path",
            import_type="from_import",
        )
    ]
    dependencies = [
        make_dependency(
            imported_module="pathlib",
            imported_name="PurePath",
        )
    ]

    result = service.validate(imports, dependencies)

    assert result.is_valid is False
    assert result.missing_dependencies == 1
    assert result.unexpected_dependencies == 1


def test_wrong_alias_is_reported(service):
    imports = [make_import(module="numpy", alias="np")]
    dependencies = [
        make_dependency(
            imported_module="numpy",
            alias="numpy",
            dependency_type="external",
        )
    ]

    result = service.validate(imports, dependencies)

    assert result.is_valid is False
    assert result.missing_dependencies == 1
    assert result.unexpected_dependencies == 1


def test_duplicate_import_without_matching_dependency_is_reported(service):
    imports = [
        make_import(module="os"),
        make_import(module="os"),
    ]
    dependencies = [make_dependency(imported_module="os")]

    result = service.validate(imports, dependencies)

    assert result.is_valid is False
    assert result.missing_dependencies == 1
    assert result.matched_dependencies == 1


def test_duplicate_dependency_without_matching_import_is_reported(service):
    imports = [make_import(module="os")]
    dependencies = [
        make_dependency(imported_module="os"),
        make_dependency(imported_module="os"),
    ]

    result = service.validate(imports, dependencies)

    assert result.is_valid is False
    assert result.unexpected_dependencies == 1
    assert result.matched_dependencies == 1


def test_duplicate_matching_records_are_counted(service):
    imports = [
        make_import(module="os"),
        make_import(module="os"),
    ]
    dependencies = [
        make_dependency(imported_module="os"),
        make_dependency(imported_module="os"),
    ]

    result = service.validate(imports, dependencies)

    assert result.is_valid is True
    assert result.matched_dependencies == 2


def test_invalid_dependency_type_is_reported(service):
    imports = [make_import(module="os")]
    dependencies = [
        make_dependency(
            imported_module="os",
            dependency_type="unknown",
        )
    ]

    result = service.validate(imports, dependencies)

    assert result.is_valid is False
    assert any(
        issue.code == "INVALID_DEPENDENCY_TYPE"
        for issue in result.issues
    )


def test_relative_import_with_external_classification_is_invalid(service):
    imports = [
        make_import(
            module="utils",
            imported_name="helper",
            import_type="from_import",
            level=1,
        )
    ]
    dependencies = [
        make_dependency(
            imported_module="utils",
            imported_name="helper",
            dependency_type="external",
            is_relative=True,
        )
    ]

    result = service.validate(imports, dependencies)

    assert result.is_valid is False
    assert result.mismatched_classifications == 1


def test_internal_module_prefix_is_classified_as_internal(service):
    imports = [make_import(module="appy.services.user")]
    dependencies = [
        make_dependency(
            imported_module="appy.services.user",
            dependency_type="internal",
        )
    ]

    result = service.validate(
        imports,
        dependencies,
        internal_modules=["appy"],
    )

    assert result.is_valid is True


def test_standard_library_submodule_is_classified_correctly(service):
    imports = [make_import(module="os.path")]
    dependencies = [
        make_dependency(imported_module="os.path")
    ]

    result = service.validate(imports, dependencies)

    assert result.is_valid is True


def test_from_import_with_alias_is_valid(service):
    imports = [
        make_import(
            module="pathlib",
            imported_name="Path",
            alias="ProjectPath",
            import_type="from_import",
        )
    ]
    dependencies = [
        make_dependency(
            imported_module="pathlib",
            imported_name="Path",
            alias="ProjectPath",
        )
    ]

    result = service.validate(imports, dependencies)

    assert result.is_valid is True


def test_import_generator_is_supported(service):
    imports = (item for item in [make_import(module="os")])
    dependencies = (item for item in [make_dependency(imported_module="os")])

    result = service.validate(imports, dependencies)

    assert result.is_valid is True
    assert result.imports_checked == 1
    assert result.dependencies_checked == 1


def test_internal_module_generator_is_supported(service):
    imports = [make_import(module="appy.services.user")]
    dependencies = [
        make_dependency(
            imported_module="appy.services.user",
            dependency_type="internal",
        )
    ]

    result = service.validate(
        imports,
        dependencies,
        internal_modules=(name for name in ["appy.services"]),
    )

    assert result.is_valid is True


@pytest.mark.parametrize(
    "imports,dependencies,internal_modules",
    [
        (None, [], ()),
        ("invalid", [], ()),
        ({"invalid": "input"}, [], ()),
        ([], None, ()),
        ([], "invalid", ()),
        ([], {"invalid": "input"}, ()),
        ([], [], None),
        ([], [], "appy"),
        ([], [], {"appy"}),
    ],
)
def test_invalid_iterable_inputs_are_rejected(
    service,
    imports,
    dependencies,
    internal_modules,
):
    with pytest.raises(DependencyConsistencyValidationError):
        service.validate(imports, dependencies, internal_modules)


def test_invalid_import_record_type_is_rejected(service):
    with pytest.raises(DependencyConsistencyValidationError):
        service.validate(["not an import"], [])


def test_invalid_dependency_record_type_is_rejected(service):
    with pytest.raises(DependencyConsistencyValidationError):
        service.validate([], ["not a dependency"])


def test_invalid_internal_module_name_is_rejected(service):
    with pytest.raises(DependencyConsistencyValidationError):
        service.validate([], [], internal_modules=["appy", " "])


def test_invalid_import_line_is_rejected(service):
    record = make_import(line=0)

    with pytest.raises(DependencyConsistencyValidationError):
        service.validate([record], [])


def test_invalid_dependency_line_is_rejected(service):
    record = make_dependency(line=0)

    with pytest.raises(DependencyConsistencyValidationError):
        service.validate([], [record])


def test_invalid_import_type_is_rejected(service):
    record = make_import(import_type="invalid")

    with pytest.raises(DependencyConsistencyValidationError):
        service.validate([record], [])


def test_invalid_import_level_is_rejected(service):
    record = make_import(level=-1)

    with pytest.raises(DependencyConsistencyValidationError):
        service.validate([record], [])


def test_invalid_dependency_relative_flag_is_rejected(service):
    record = make_dependency(is_relative="yes")

    with pytest.raises(DependencyConsistencyValidationError):
        service.validate([], [record])


def test_invalid_dependency_type_value_is_reported_not_raised(service):
    imports = [make_import(module="os")]
    dependencies = [
        make_dependency(
            imported_module="os",
            dependency_type="not-a-valid-type",
        )
    ]

    result = service.validate(imports, dependencies)

    assert result.is_valid is False
    assert any(
        issue.code == "INVALID_DEPENDENCY_TYPE"
        for issue in result.issues
    )


def test_result_counts_are_consistent(service):
    imports = [
        make_import(module="os", line=1),
        make_import(module="requests", line=2),
    ]
    dependencies = [
        make_dependency(imported_module="os", line=1),
    ]

    result = service.validate(imports, dependencies)

    assert result.imports_checked == 2
    assert result.dependencies_checked == 1
    assert result.matched_dependencies == 1
    assert result.missing_dependencies == 1
    assert result.unexpected_dependencies == 0


def test_error_and_warning_counts_are_available(service):
    result = service.validate(
        [make_import(module="os")],
        [],
    )

    assert result.error_count == 1
    assert result.warning_count == 0
    assert result.total_issues == 1


def test_healthy_property_matches_validity(service):
    valid_result = service.validate(
        [make_import(module="os")],
        [make_dependency(imported_module="os")],
    )
    invalid_result = service.validate(
        [make_import(module="os")],
        [],
    )

    assert valid_result.healthy is True
    assert invalid_result.healthy is False


def test_validation_does_not_modify_inputs(service):
    imports = [make_import(module="os")]
    dependencies = [make_dependency(imported_module="os")]

    original_imports = list(imports)
    original_dependencies = list(dependencies)

    service.validate(imports, dependencies)

    assert imports == original_imports
    assert dependencies == original_dependencies


def test_validation_is_deterministic(service):
    imports = [
        make_import(module="requests", line=2),
        make_import(module="os", line=1),
    ]
    dependencies = [
        make_dependency(
            imported_module="requests",
            dependency_type="external",
            line=2,
        ),
        make_dependency(imported_module="os", line=1),
    ]

    first = service.validate(imports, dependencies)
    second = service.validate(imports, dependencies)

    assert first == second


def test_issues_are_sorted_deterministically(service):
    imports = [
        make_import(filename="z.py", module="os", line=3),
        make_import(filename="a.py", module="sys", line=1),
    ]

    result = service.validate(imports, [])

    assert list(result.issues) == sorted(
        result.issues,
        key=lambda issue: (
            issue.source_file,
            issue.line,
            issue.code,
            issue.message,
        ),
    )


def test_custom_dependency_analyzer_is_used():
    class CustomAnalyzer:
        DEPENDENCY_INTERNAL = "internal"
        DEPENDENCY_EXTERNAL = "external"
        DEPENDENCY_STANDARD_LIBRARY = "standard_library"
        DEPENDENCY_UNRESOLVED = "unresolved"

        def analyze(self, imports, internal_modules=()):
            return tuple(
                DependencyRecord(
                    source_file=item.filename,
                    imported_module=item.module,
                    imported_name=item.imported_name,
                    alias=item.alias,
                    dependency_type="external",
                    line=item.line,
                    is_relative=item.is_relative,
                )
                for item in imports
            )

    service = DependencyConsistencyValidationService(
        dependency_analyzer=CustomAnalyzer()
    )
    imports = [make_import(module="custom_module")]
    dependencies = [
        make_dependency(
            imported_module="custom_module",
            dependency_type="external",
        )
    ]

    result = service.validate(imports, dependencies)

    assert result.is_valid is True


def test_issue_model_rejects_empty_code():
    with pytest.raises(ValueError):
        DependencyConsistencyIssue(
            code="",
            message="Invalid dependency",
        )


def test_issue_model_rejects_invalid_severity():
    with pytest.raises(TypeError):
        DependencyConsistencyIssue(
            code="INVALID",
            message="Invalid dependency",
            severity="error",
        )


def test_result_model_rejects_negative_counts():
    with pytest.raises(ValueError):
        DependencyConsistencyValidationResult(
            is_valid=True,
            imports_checked=-1,
            dependencies_checked=0,
            matched_dependencies=0,
            missing_dependencies=0,
            unexpected_dependencies=0,
            mismatched_classifications=0,
            issues=(),
        )


def test_valid_result_cannot_contain_issues():
    with pytest.raises(ValueError):
        DependencyConsistencyValidationResult(
            is_valid=True,
            imports_checked=0,
            dependencies_checked=0,
            matched_dependencies=0,
            missing_dependencies=0,
            unexpected_dependencies=0,
            mismatched_classifications=0,
            issues=(
                DependencyConsistencyIssue(
                    code="TEST",
                    message="Test issue",
                ),
            ),
        )


def test_invalid_result_requires_issues():
    with pytest.raises(ValueError):
        DependencyConsistencyValidationResult(
            is_valid=False,
            imports_checked=0,
            dependencies_checked=0,
            matched_dependencies=0,
            missing_dependencies=0,
            unexpected_dependencies=0,
            mismatched_classifications=0,
            issues=(),
        )
