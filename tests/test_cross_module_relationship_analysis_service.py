
import ast

import pytest

from app.application.cross_module_relationship_analysis_service import (
    CrossModuleRelationshipAnalysisError,
    CrossModuleRelationshipAnalysisService,
    CrossModuleRelationshipType,
    CrossModuleResolutionStatus,
)
from app.application.language_parser import ParsedSource


@pytest.fixture
def service():
    return CrossModuleRelationshipAnalysisService()


def parsed_source(
    filename,
    source,
    language="python",
):
    # The service only analyzes Python ASTs. For unsupported languages,
    # use a harmless AST placeholder so the service can skip the file.
    source_tree = (
        ast.parse(source)
        if language.lower() == "python"
        else ast.parse("pass")
    )

    return ParsedSource(
        language=language,
        filename=filename,
        tree=source_tree,
        line_count=len(source.splitlines()),
    )


def test_empty_sources_returns_empty_result(service):
    result = service.analyze({})

    assert result.total_files == 0
    assert result.analyzed_files == 0
    assert result.total_modules == 0
    assert result.total_entities == 0
    assert result.cross_module_calls == 0
    assert result.module_relationships == ()
    assert result.healthy is True


def test_analyzes_single_python_module(service):
    sources = {
        "main.py": parsed_source(
            "main.py",
            """
def first():
    second()

def second():
    pass
""",
        )
    }

    result = service.analyze(sources)

    assert result.total_files == 1
    assert result.analyzed_files == 1
    assert result.skipped_files == 0
    assert result.total_modules == 1
    assert result.cross_module_calls == 0


def test_detects_cross_module_function_call(service):
    sources = {
        "main.py": parsed_source(
            "main.py",
            """
def main():
    helper()
""",
        ),
        "helper.py": parsed_source(
            "helper.py",
            """
def helper():
    return True
""",
        ),
    }

    result = service.analyze(sources)

    assert result.cross_module_calls == 1
    assert result.resolved_calls == 1
    assert result.unresolved_calls == 0

    relationship = result.module_relationships[0]

    assert relationship.source_module == "main"
    assert relationship.target_module == "helper"
    assert relationship.relationship_count == 1


def test_resolves_qualified_module_function_call(service):
    sources = {
        "main.py": parsed_source(
            "main.py",
            """
def main():
    helper.process()
""",
        ),
        "helper.py": parsed_source(
            "helper.py",
            """
def process():
    return 1
""",
        ),
    }

    result = service.analyze(sources)

    assert result.cross_module_calls == 1
    assert result.resolved_calls == 1
    assert (
        result.cross_module_call_records[0].target_entity
        == "helper.process"
    )


def test_detects_cross_module_method_call(service):
    sources = {
        "main.py": parsed_source(
            "main.py",
            """
def run():
    worker.process()
""",
        ),
        "worker.py": parsed_source(
            "worker.py",
            """
class Worker:
    def process(self):
        return True
""",
        ),
    }

    result = service.analyze(sources)

    assert result.cross_module_calls == 1
    assert result.resolved_calls == 1
    assert (
        result.cross_module_call_records[0].target_module
        == "worker"
    )


def test_identifies_relationship_type_for_function_caller(service):
    sources = {
        "main.py": parsed_source(
            "main.py",
            """
def run():
    helper()
""",
        ),
        "helper.py": parsed_source(
            "helper.py",
            """
def helper():
    pass
""",
        ),
    }

    result = service.analyze(sources)

    assert (
        result.cross_module_call_records[0].relationship_type
        == CrossModuleRelationshipType.FUNCTION_CALL
    )


def test_identifies_relationship_type_for_method_caller(service):
    sources = {
        "main.py": parsed_source(
            "main.py",
            """
class Runner:
    def run(self):
        helper()
""",
        ),
        "helper.py": parsed_source(
            "helper.py",
            """
def helper():
    pass
""",
        ),
    }

    result = service.analyze(sources)

    assert (
        result.cross_module_call_records[0].relationship_type
        == CrossModuleRelationshipType.METHOD_CALL
    )


def test_aggregates_multiple_calls_between_same_modules(service):
    sources = {
        "main.py": parsed_source(
            "main.py",
            """
def first():
    helper_one()
    helper_two()
""",
        ),
        "helpers.py": parsed_source(
            "helpers.py",
            """
def helper_one():
    pass

def helper_two():
    pass
""",
        ),
    }

    result = service.analyze(sources)

    assert result.cross_module_calls == 2
    assert len(result.module_relationships) == 1
    assert result.module_relationships[0].relationship_count == 2


def test_detects_relationships_in_both_directions(service):
    sources = {
        "alpha.py": parsed_source(
            "alpha.py",
            """
def alpha():
    beta()
""",
        ),
        "beta.py": parsed_source(
            "beta.py",
            """
def beta():
    alpha()
""",
        ),
    }

    result = service.analyze(sources)

    assert result.cross_module_calls == 2
    assert len(result.module_relationships) == 2


def test_does_not_count_same_module_calls_as_cross_module(service):
    sources = {
        "main.py": parsed_source(
            "main.py",
            """
def first():
    second()

def second():
    pass
""",
        )
    }

    result = service.analyze(sources)

    assert result.cross_module_calls == 0
    assert result.module_relationships == ()


def test_ignores_calls_to_unknown_simple_names(service):
    sources = {
        "main.py": parsed_source(
            "main.py",
            """
def run():
    external_function()
""",
        ),
        "helper.py": parsed_source(
            "helper.py",
            """
def helper():
    pass
""",
        ),
    }

    result = service.analyze(sources)

    assert result.cross_module_calls == 0
    assert result.unresolved_calls == 0


def test_reports_unresolved_qualified_target(service):
    sources = {
        "main.py": parsed_source(
            "main.py",
            """
def run():
    helper.missing_function()
""",
        ),
        "helper.py": parsed_source(
            "helper.py",
            """
def existing_function():
    pass
""",
        ),
    }

    result = service.analyze(sources)

    assert result.cross_module_calls == 1
    assert result.unresolved_calls == 1
    assert result.has_unresolved_references is True
    assert (
        result.cross_module_call_records[0].resolution_status
        == CrossModuleResolutionStatus.UNRESOLVED
    )


def test_ignores_non_python_sources(service):
    sources = {
        "main.py": parsed_source(
            "main.py",
            """
def run():
    pass
""",
        ),
        "frontend.js": parsed_source(
            "frontend.js",
            "function run() {}",
            language="javascript",
        ),
    }

    result = service.analyze(sources)

    assert result.total_files == 2
    assert result.analyzed_files == 1
    assert result.skipped_files == 1
    assert result.total_modules == 1


def test_skips_all_non_python_sources(service):
    sources = {
        "frontend.js": parsed_source(
            "frontend.js",
            "function run() {}",
            language="javascript",
        ),
    }

    result = service.analyze(sources)

    assert result.analyzed_files == 0
    assert result.skipped_files == 1
    assert result.total_modules == 0
    assert result.total_calls == 0


def test_counts_total_calls_from_all_python_modules(service):
    sources = {
        "main.py": parsed_source(
            "main.py",
            """
def run():
    first()
    second()
""",
        ),
        "helper.py": parsed_source(
            "helper.py",
            """
def first():
    pass

def second():
    pass
""",
        ),
    }

    result = service.analyze(sources)

    assert result.total_calls == 2
    assert result.cross_module_calls == 2


def test_resolution_percentage_for_resolved_calls(service):
    sources = {
        "main.py": parsed_source(
            "main.py",
            """
def run():
    helper()
""",
        ),
        "helper.py": parsed_source(
            "helper.py",
            """
def helper():
    pass
""",
        ),
    }

    result = service.analyze(sources)

    assert result.resolution_percentage == 100.0


def test_resolution_percentage_for_no_cross_module_calls(service):
    result = service.analyze(
        {
            "main.py": parsed_source(
                "main.py",
                """
def run():
    pass
""",
            )
        }
    )

    assert result.resolution_percentage == 100.0


def test_result_healthy_when_all_references_resolve(service):
    sources = {
        "main.py": parsed_source(
            "main.py",
            """
def run():
    helper()
""",
        ),
        "helper.py": parsed_source(
            "helper.py",
            """
def helper():
    pass
""",
        ),
    }

    result = service.analyze(sources)

    assert result.healthy is True


def test_result_not_healthy_when_reference_is_unresolved(service):
    sources = {
        "main.py": parsed_source(
            "main.py",
            """
def run():
    helper.missing()
""",
        ),
        "helper.py": parsed_source(
            "helper.py",
            """
def existing():
    pass
""",
        ),
    }

    result = service.analyze(sources)

    assert result.healthy is False


def test_supports_nested_source_paths(service):
    sources = {
        "app/main.py": parsed_source(
            "app/main.py",
            """
def run():
    helper()
""",
        ),
        "app/helper.py": parsed_source(
            "app/helper.py",
            """
def helper():
    pass
""",
        ),
    }

    result = service.analyze(sources)

    assert result.total_modules == 2
    assert result.cross_module_calls == 1
    assert (
        result.module_relationships[0].source_module
        == "app.main"
    )
    assert (
        result.module_relationships[0].target_module
        == "app.helper"
    )


def test_supports_package_init_module_paths(service):
    sources = {
        "app/main.py": parsed_source(
            "app/main.py",
            """
def run():
    helper()
""",
        ),
        "app/helpers/__init__.py": parsed_source(
            "app/helpers/__init__.py",
            """
def helper():
    pass
""",
        ),
    }

    result = service.analyze(sources)

    assert result.total_modules == 2
    assert result.cross_module_calls == 1


def test_rejects_non_mapping_input(service):
    with pytest.raises(
        CrossModuleRelationshipAnalysisError,
        match="mapping",
    ):
        service.analyze([])


@pytest.mark.parametrize(
    "invalid_path",
    [
        "",
        "/absolute/main.py",
        "../main.py",
        "app/../main.py",
        "app//main.py",
        "./main.py",
    ],
)
def test_rejects_invalid_source_paths(service, invalid_path):
    with pytest.raises(CrossModuleRelationshipAnalysisError):
        service.analyze(
            {
                invalid_path: parsed_source(
                    invalid_path,
                    "pass",
                )
            }
        )


def test_rejects_invalid_parsed_source(service):
    with pytest.raises(
        CrossModuleRelationshipAnalysisError,
        match="Invalid ParsedSource",
    ):
        service.analyze({"main.py": "not a parsed source"})


def test_rejects_mismatched_filename_and_key(service):
    sources = {
        "main.py": parsed_source(
            "different.py",
            "pass",
        )
    }

    with pytest.raises(
        CrossModuleRelationshipAnalysisError,
        match="does not match",
    ):
        service.analyze(sources)


def test_rejects_duplicate_module_names(service):
    sources = {
        "main.py": parsed_source("main.py", "pass"),
        "folder/main.py": parsed_source(
            "folder/main.py",
            "pass",
        ),
    }

    with pytest.raises(
        CrossModuleRelationshipAnalysisError,
        match="Duplicate module name",
    ):
        service.analyze(sources)


def test_results_are_deterministic(service):
    first = {
        "main.py": parsed_source(
            "main.py",
            """
def run():
    beta()
    alpha()
""",
        ),
        "alpha.py": parsed_source(
            "alpha.py",
            "def alpha(): pass",
        ),
        "beta.py": parsed_source(
            "beta.py",
            "def beta(): pass",
        ),
    }

    second = {
        "beta.py": first["beta.py"],
        "alpha.py": first["alpha.py"],
        "main.py": first["main.py"],
    }

    result_one = service.analyze(first)
    result_two = service.analyze(second)

    assert (
        result_one.cross_module_call_records
        == result_two.cross_module_call_records
    )
    assert (
        result_one.module_relationships
        == result_two.module_relationships
    )


def test_records_source_and_target_file_paths(service):
    sources = {
        "src/main.py": parsed_source(
            "src/main.py",
            """
def run():
    helper()
""",
        ),
        "src/helper.py": parsed_source(
            "src/helper.py",
            """
def helper():
    pass
""",
        ),
    }

    result = service.analyze(sources)
    record = result.cross_module_call_records[0]

    assert record.source_file == "src/main.py"
    assert record.target_file == "src/helper.py"


def test_relationship_contains_its_call_records(service):
    sources = {
        "main.py": parsed_source(
            "main.py",
            """
def run():
    helper()
""",
        ),
        "helper.py": parsed_source(
            "helper.py",
            """
def helper():
    pass
""",
        ),
    }

    result = service.analyze(sources)
    relationship = result.module_relationships[0]

    assert relationship.calls == result.cross_module_call_records
    assert relationship.relationship_count == len(
        relationship.calls
    )


def test_counts_entities_from_python_modules(service):
    sources = {
        "main.py": parsed_source(
            "main.py",
            """
class Runner:
    def run(self):
        helper()

def standalone():
    pass
""",
        ),
        "helper.py": parsed_source(
            "helper.py",
            """
def helper():
    pass
""",
        ),
    }

    result = service.analyze(sources)

    assert result.total_entities == 6


def test_excludes_module_and_class_entities_from_call_targets(service):
    sources = {
        "main.py": parsed_source(
            "main.py",
            """
def run():
    helper.Worker()
""",
        ),
        "helper.py": parsed_source(
            "helper.py",
            """
class Worker:
    def process(self):
        pass
""",
        ),
    }

    result = service.analyze(sources)

    assert result.cross_module_calls == 1


def test_supports_async_function_targets(service):
    sources = {
        "main.py": parsed_source(
            "main.py",
            """
def run():
    helper()
""",
        ),
        "helper.py": parsed_source(
            "helper.py",
            """
async def helper():
    return True
""",
        ),
    }

    result = service.analyze(sources)

    assert result.cross_module_calls == 1
    assert result.resolved_calls == 1


def test_relationship_types_are_sorted(service):
    sources = {
        "main.py": parsed_source(
            "main.py",
            """
def run():
    helper()

class Runner:
    def execute(self):
        helper()
""",
        ),
        "helper.py": parsed_source(
            "helper.py",
            """
def helper():
    pass
""",
        ),
    }

    result = service.analyze(sources)

    relationship = result.module_relationships[0]

    assert relationship.relationship_types == tuple(
        sorted(relationship.relationship_types)
    )
