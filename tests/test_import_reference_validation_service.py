
"""Tests for import and reference validation."""

import pytest

from appy.application.import_analyzer import ImportRecord
from appy.application.import_reference_validation_service import (
    ImportReferenceIssue,
    ImportReferenceRecord,
    ImportReferenceSeverity,
    ImportReferenceStatus,
    ImportReferenceValidationError,
    ImportReferenceValidationResult,
    ImportReferenceValidationService,
)


@pytest.fixture
def service():
    return ImportReferenceValidationService()


def make_import(
    filename="src/main.py",
    module="appy.services.user_service",
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


def test_empty_inputs_return_valid_result(service):
    result = service.validate([], [])

    assert result.total_imports == 0
    assert result.valid_imports == 0
    assert result.invalid_imports == 0
    assert result.unresolved_imports == 0
    assert result.external_imports == 0
    assert result.records == ()
    assert result.issues == ()
    assert result.is_valid is True


def test_known_internal_module_is_valid(service):
    result = service.validate(
        [make_import()],
        ["appy.services.user_service"],
    )

    assert result.valid_imports == 1
    assert result.invalid_imports == 0
    assert result.records[0].status == ImportReferenceStatus.VALID


def test_module_path_with_py_extension_is_normalized(service):
    result = service.validate(
        [make_import(module="appy/services/user_service")],
        ["appy/services/user_service.py"],
    )

    assert result.valid_imports == 1


def test_module_path_with_backslashes_is_normalized(service):
    result = service.validate(
        [make_import(module="appy.services.user_service")],
        ["appy\\services\\user_service.py"],
    )

    assert result.valid_imports == 1


def test_module_child_is_resolved_from_known_submodule(service):
    result = service.validate(
        [make_import(module="appy.services")],
        ["appy.services.user_service"],
    )

    assert result.valid_imports == 1


def test_known_package_init_module_is_resolved(service):
    result = service.validate(
        [make_import(module="appy.services")],
        ["appy.services.__init__"],
    )

    assert result.valid_imports == 1


def test_missing_repository_module_is_external(service):
    result = service.validate(
        [make_import(module="requests")],
        ["appy.services.user_service"],
    )

    assert result.external_imports == 1
    assert result.invalid_imports == 0
    assert result.records[0].status == ImportReferenceStatus.EXTERNAL


def test_relative_import_is_unresolved(service):
    result = service.validate(
        [
            make_import(
                module="helpers",
                imported_name="format_name",
                import_type="from_import",
                level=1,
            )
        ],
        ["appy.helpers"],
    )

    assert result.unresolved_imports == 1
    assert result.records[0].status == ImportReferenceStatus.UNRESOLVED
    assert result.issues[0].code == "RELATIVE_IMPORT_UNRESOLVED"
    assert result.warning_count == 1


def test_relative_import_is_not_marked_invalid(service):
    result = service.validate(
        [make_import(module="missing", level=2)],
        [],
    )

    assert result.invalid_imports == 0
    assert result.unresolved_imports == 1
    assert result.is_valid is True


def test_imported_symbol_is_valid_when_exported(service):
    result = service.validate(
        [
            make_import(
                module="appy.services.user_service",
                imported_name="UserService",
                import_type="from_import",
            )
        ],
        ["appy.services.user_service"],
        module_exports={
            "appy.services.user_service": ["UserService", "create_user"],
        },
    )

    assert result.valid_imports == 1
    assert result.invalid_imports == 0


def test_missing_imported_symbol_is_invalid(service):
    result = service.validate(
        [
            make_import(
                module="appy.services.user_service",
                imported_name="MissingService",
                import_type="from_import",
            )
        ],
        ["appy.services.user_service"],
        module_exports={
            "appy.services.user_service": ["UserService"],
        },
    )

    assert result.invalid_imports == 1
    assert result.valid_imports == 0
    assert result.issues[0].code == "IMPORTED_SYMBOL_NOT_FOUND"
    assert result.issues[0].severity == ImportReferenceSeverity.ERROR


def test_symbol_is_not_guessed_when_export_inventory_is_missing(service):
    result = service.validate(
        [
            make_import(
                module="appy.services.user_service",
                imported_name="UnknownSymbol",
                import_type="from_import",
            )
        ],
        ["appy.services.user_service"],
    )

    assert result.valid_imports == 1
    assert result.invalid_imports == 0


def test_import_alias_does_not_change_symbol_validation(service):
    result = service.validate(
        [
            make_import(
                module="appy.services.user_service",
                imported_name="UserService",
                alias="Service",
                import_type="from_import",
            )
        ],
        ["appy.services.user_service"],
        module_exports={
            "appy.services.user_service": ["UserService"],
        },
    )

    assert result.valid_imports == 1


def test_external_module_symbol_is_not_checked_against_internal_exports(service):
    result = service.validate(
        [
            make_import(
                module="requests",
                imported_name="get",
                import_type="from_import",
            )
        ],
        ["appy.services.user_service"],
        module_exports={
            "appy.services.user_service": ["UserService"],
        },
    )

    assert result.external_imports == 1
    assert result.invalid_imports == 0


def test_missing_module_name_is_unresolved(service):
    result = service.validate(
        [make_import(module=None)],
        ["appy.services.user_service"],
    )

    assert result.unresolved_imports == 1
    assert result.issues[0].code == "MISSING_IMPORT_MODULE"


def test_module_name_with_only_dots_is_invalid(service):
    result = service.validate(
        [make_import(module="...")],
        ["appy.services.user_service"],
    )

    assert result.invalid_imports == 1
    assert result.issues[0].code == "INVALID_IMPORT_MODULE"


def test_multiple_imports_are_counted_independently(service):
    imports = [
        make_import(module="appy.services.user_service", line=1),
        make_import(module="requests", line=2),
        make_import(module="missing_module", line=3, level=1),
    ]

    result = service.validate(
        imports,
        ["appy.services.user_service"],
    )

    assert result.total_imports == 3
    assert result.valid_imports == 1
    assert result.external_imports == 1
    assert result.unresolved_imports == 1


def test_issue_records_include_source_location(service):
    result = service.validate(
        [make_import(module="missing_module", filename="src/api.py", line=12)],
        [],
    )

    issue = result.issues[0]

    assert issue.source_file == "src/api.py"
    assert issue.line == 12
    assert issue.imported_module == "missing_module"


def test_records_preserve_import_metadata(service):
    record = make_import(
        filename="src/api.py",
        module="appy.services.user_service",
        imported_name="UserService",
        alias="Service",
        import_type="from_import",
        line=8,
    )

    result = service.validate(
        [record],
        ["appy.services.user_service"],
    )

    validated = result.records[0]

    assert validated.source_file == "src/api.py"
    assert validated.line == 8
    assert validated.imported_module == "appy.services.user_service"
    assert validated.imported_name == "UserService"
    assert validated.alias == "Service"


def test_is_valid_is_false_when_invalid_import_exists(service):
    result = service.validate(
        [
            make_import(
                module="appy.services.user_service",
                imported_name="Missing",
                import_type="from_import",
            )
        ],
        ["appy.services.user_service"],
        module_exports={"appy.services.user_service": ["UserService"]},
    )

    assert result.is_valid is False
    assert result.healthy is False


def test_unresolved_import_does_not_make_result_invalid(service):
    result = service.validate(
        [make_import(module="helpers", level=1)],
        [],
    )

    assert result.is_valid is True
    assert result.has_unresolved_imports is True


def test_error_and_warning_counts(service):
    result = service.validate(
        [
            make_import(
                module="appy.services.user_service",
                imported_name="Missing",
                import_type="from_import",
                line=1,
            ),
            make_import(module="helpers", level=1, line=2),
            make_import(module="requests", line=3),
        ],
        ["appy.services.user_service"],
        module_exports={"appy.services.user_service": ["UserService"]},
    )

    assert result.error_count == 1
    assert result.warning_count == 2


def test_import_generator_is_supported(service):
    imports = (item for item in [make_import()])

    result = service.validate(
        imports,
        ["appy.services.user_service"],
    )

    assert result.total_imports == 1
    assert result.valid_imports == 1


def test_internal_module_generator_is_supported(service):
    modules = (item for item in ["appy.services.user_service"])

    result = service.validate(
        [make_import()],
        modules,
    )

    assert result.valid_imports == 1


@pytest.mark.parametrize(
    "imports,modules",
    [
        (None, []),
        ("invalid", []),
        ({"invalid": "input"}, []),
        ([], None),
        ([], "appy.services"),
        ([], {"appy.services"}),
        ([], {"appy.services": "value"}),
    ],
)
def test_invalid_import_or_module_inputs_are_rejected(
    service,
    imports,
    modules,
):
    with pytest.raises(ImportReferenceValidationError):
        service.validate(imports, modules)


def test_invalid_import_record_type_is_rejected(service):
    with pytest.raises(ImportReferenceValidationError):
        service.validate(["not an ImportRecord"], [])


def test_invalid_module_name_is_rejected(service):
    with pytest.raises(ImportReferenceValidationError):
        service.validate([], [" "])


def test_invalid_export_mapping_type_is_rejected(service):
    with pytest.raises(ImportReferenceValidationError):
        service.validate([], [], module_exports=["not a mapping"])


@pytest.mark.parametrize(
    "exports",
    [
        {"appy.services.user_service": "UserService"},
        {"appy.services.user_service": None},
        {"appy.services.user_service": {"UserService"}},
        {" ": ["UserService"]},
        {"appy.services.user_service": [""]},
    ],
)
def test_invalid_export_values_are_rejected(service, exports):
    with pytest.raises(ImportReferenceValidationError):
        service.validate([], [], module_exports=exports)


def test_duplicate_normalized_export_modules_are_rejected(service):
    with pytest.raises(ImportReferenceValidationError):
        service.validate(
            [],
            [],
            module_exports={
                "appy/services/user_service.py": ["UserService"],
                "appy.services.user_service": ["create_user"],
            },
        )


def test_invalid_import_line_is_rejected(service):
    with pytest.raises(ImportReferenceValidationError):
        service.validate(
            [make_import(line=0)],
            [],
        )


def test_invalid_import_level_is_rejected(service):
    with pytest.raises(ImportReferenceValidationError):
        service.validate(
            [make_import(level=-1)],
            [],
        )


def test_invalid_import_type_is_rejected(service):
    with pytest.raises(ImportReferenceValidationError):
        service.validate(
            [make_import(import_type="invalid")],
            [],
        )


def test_analysis_does_not_modify_inputs(service):
    imports = [make_import()]
    modules = ["appy.services.user_service"]
    exports = {"appy.services.user_service": ["UserService"]}

    original_imports = list(imports)
    original_modules = list(modules)
    original_exports = dict(exports)

    service.validate(imports, modules, exports)

    assert imports == original_imports
    assert modules == original_modules
    assert exports == original_exports


def test_validation_is_deterministic(service):
    imports = [
        make_import(module="requests", line=2),
        make_import(module="missing", level=1, line=1),
    ]

    first = service.validate(imports, ["appy.services.user_service"])
    second = service.validate(imports, ["appy.services.user_service"])

    assert first == second


def test_issues_are_sorted_by_source_and_line(service):
    imports = [
        make_import(module="requests", filename="z.py", line=5),
        make_import(module="missing", filename="a.py", line=2, level=1),
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


def test_result_rejects_inconsistent_status_counts():
    with pytest.raises(ValueError):
        ImportReferenceValidationResult(
            total_imports=1,
            valid_imports=1,
            invalid_imports=1,
            unresolved_imports=0,
            external_imports=0,
            records=(),
            issues=(),
        )


def test_result_rejects_record_count_mismatch():
    with pytest.raises(ValueError):
        ImportReferenceValidationResult(
            total_imports=1,
            valid_imports=1,
            invalid_imports=0,
            unresolved_imports=0,
            external_imports=0,
            records=(),
            issues=(),
        )


def test_issue_rejects_invalid_severity():
    with pytest.raises(TypeError):
        ImportReferenceIssue(
            code="INVALID",
            message="Invalid import",
            source_file="main.py",
            line=1,
            severity="error",
            status=ImportReferenceStatus.INVALID,
        )


def test_record_rejects_invalid_status():
    with pytest.raises(TypeError):
        ImportReferenceRecord(
            source_file="main.py",
            line=1,
            imported_module="os",
            imported_name=None,
            alias=None,
            status="valid",
            message="Valid",
        )


def test_standard_library_import_is_external_without_repository_inventory(service):
    result = service.validate(
        [make_import(module="os")],
        ["appy.services.user_service"],
    )

    assert result.external_imports == 1
    assert result.invalid_imports == 0
