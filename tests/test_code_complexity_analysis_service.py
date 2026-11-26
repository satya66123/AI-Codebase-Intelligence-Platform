
import pytest

from appy.application.code_complexity_analysis_service import (
    CodeComplexityAnalysisError,
    CodeComplexityAnalysisResult,
    CodeComplexityAnalysisService,
    ComplexitySeverity,
    FileComplexityResult,
    FunctionComplexity,
)


@pytest.fixture
def service():
    return CodeComplexityAnalysisService()


def test_default_thresholds(service):
    assert service.high_cyclomatic_threshold == 10
    assert service.critical_cyclomatic_threshold == 20
    assert service.high_cognitive_threshold == 15
    assert service.critical_cognitive_threshold == 30


@pytest.mark.parametrize(
    "kwargs",
    [
        {"high_cyclomatic_threshold": 0},
        {"critical_cyclomatic_threshold": 0},
        {"high_cognitive_threshold": 0},
        {"critical_cognitive_threshold": 0},
        {"high_nesting_threshold": 0},
        {"critical_nesting_threshold": 0},
        {"high_cyclomatic_threshold": True},
    ],
)
def test_invalid_thresholds_are_rejected(kwargs):
    with pytest.raises(CodeComplexityAnalysisError):
        CodeComplexityAnalysisService(**kwargs)


def test_critical_cyclomatic_threshold_must_not_be_lower():
    with pytest.raises(CodeComplexityAnalysisError):
        CodeComplexityAnalysisService(
            high_cyclomatic_threshold=10,
            critical_cyclomatic_threshold=5,
        )


def test_critical_cognitive_threshold_must_not_be_lower():
    with pytest.raises(CodeComplexityAnalysisError):
        CodeComplexityAnalysisService(
            high_cognitive_threshold=10,
            critical_cognitive_threshold=5,
        )


def test_critical_nesting_threshold_must_not_be_lower():
    with pytest.raises(CodeComplexityAnalysisError):
        CodeComplexityAnalysisService(
            high_nesting_threshold=5,
            critical_nesting_threshold=3,
        )


def test_empty_repository(service):
    result = service.analyze({})

    assert result.total_files == 0
    assert result.analyzed_files == 0
    assert result.skipped_files == 0
    assert result.total_functions == 0
    assert result.average_cyclomatic_complexity == 0
    assert result.maximum_cyclomatic_complexity == 0
    assert result.average_cognitive_complexity == 0
    assert result.maximum_cognitive_complexity == 0
    assert result.maximum_nesting_depth == 0


def test_analyze_requires_mapping(service):
    with pytest.raises(CodeComplexityAnalysisError):
        service.analyze("invalid")


@pytest.mark.parametrize(
    "path",
    [
        "",
        "../outside.py",
        "/absolute/file.py",
        "./file.py",
        "folder//file.py",
        "C:\\outside\\file.py",
    ],
)
def test_invalid_source_path_is_rejected(service, path):
    with pytest.raises(CodeComplexityAnalysisError):
        service.analyze({path: "pass"})


def test_source_content_must_be_string(service):
    with pytest.raises(CodeComplexityAnalysisError):
        service.analyze({"module.py": 123})


def test_non_python_files_are_skipped(service):
    result = service.analyze(
        {
            "README.md": "# Project",
            "config.json": "{}",
            "module.py": "def example():\n    return 1\n",
        }
    )

    assert result.total_files == 3
    assert result.analyzed_files == 1
    assert result.skipped_files == 2


def test_python_file_is_analyzed(service):
    result = service.analyze(
        {"module.py": "def example():\n    return 1\n"}
    )

    assert result.analyzed_files == 1
    assert result.total_functions == 1


def test_pythonw_file_is_analyzed(service):
    result = service.analyze(
        {"module.pyw": "def example():\n    return 1\n"}
    )

    assert result.analyzed_files == 1


def test_lines_of_code_excludes_blank_lines(service):
    result = service.analyze(
        {"module.py": "def example():\n\n    return 1\n\n"}
    )

    assert result.total_lines_of_code == 2


def test_simple_function_has_cyclomatic_complexity_one(service):
    result = service.analyze(
        {
            "module.py": (
                "def example(value):\n"
                "    return value + 1\n"
            )
        }
    )

    function = result.functions[0]
    assert function.cyclomatic_complexity == 1


def test_if_increases_cyclomatic_complexity(service):
    result = service.analyze(
        {
            "module.py": (
                "def example(value):\n"
                "    if value:\n"
                "        return 1\n"
                "    return 0\n"
            )
        }
    )

    assert result.functions[0].cyclomatic_complexity == 2


def test_if_else_does_not_count_else_as_extra_decision(service):
    result = service.analyze(
        {
            "module.py": (
                "def example(value):\n"
                "    if value:\n"
                "        return 1\n"
                "    else:\n"
                "        return 0\n"
            )
        }
    )

    assert result.functions[0].cyclomatic_complexity == 2


def test_elif_increases_cyclomatic_complexity(service):
    result = service.analyze(
        {
            "module.py": (
                "def example(value):\n"
                "    if value == 1:\n"
                "        return 1\n"
                "    elif value == 2:\n"
                "        return 2\n"
                "    return 0\n"
            )
        }
    )

    assert result.functions[0].cyclomatic_complexity == 3


def test_for_loop_increases_cyclomatic_complexity(service):
    result = service.analyze(
        {
            "module.py": (
                "def example(items):\n"
                "    for item in items:\n"
                "        print(item)\n"
            )
        }
    )

    assert result.functions[0].cyclomatic_complexity == 2


def test_while_loop_increases_cyclomatic_complexity(service):
    result = service.analyze(
        {
            "module.py": (
                "def example(value):\n"
                "    while value:\n"
                "        value -= 1\n"
            )
        }
    )

    assert result.functions[0].cyclomatic_complexity == 2


def test_exception_handler_increases_cyclomatic_complexity(service):
    result = service.analyze(
        {
            "module.py": (
                "def example():\n"
                "    try:\n"
                "        return int('1')\n"
                "    except ValueError:\n"
                "        return 0\n"
            )
        }
    )

    assert result.functions[0].cyclomatic_complexity == 2


def test_boolean_operator_increases_cyclomatic_complexity(service):
    result = service.analyze(
        {
            "module.py": (
                "def example(a, b):\n"
                "    return a and b\n"
            )
        }
    )

    assert result.functions[0].cyclomatic_complexity == 2


def test_multiple_boolean_operators_increase_complexity(service):
    result = service.analyze(
        {
            "module.py": (
                "def example(a, b, c):\n"
                "    return a and b and c\n"
            )
        }
    )

    assert result.functions[0].cyclomatic_complexity == 3


def test_conditional_expression_increases_complexity(service):
    result = service.analyze(
        {
            "module.py": (
                "def example(value):\n"
                "    return 1 if value else 0\n"
            )
        }
    )

    assert result.functions[0].cyclomatic_complexity == 2


def test_comprehension_filter_increases_complexity(service):
    result = service.analyze(
        {
            "module.py": (
                "def example(items):\n"
                "    return [item for item in items if item]\n"
            )
        }
    )

    assert result.functions[0].cyclomatic_complexity == 2


def test_nested_if_increases_cyclomatic_complexity(service):
    result = service.analyze(
        {
            "module.py": (
                "def example(a, b):\n"
                "    if a:\n"
                "        if b:\n"
                "            return 1\n"
                "    return 0\n"
            )
        }
    )

    assert result.functions[0].cyclomatic_complexity == 3


def test_cognitive_complexity_simple_function_is_zero(service):
    result = service.analyze(
        {
            "module.py": (
                "def example(value):\n"
                "    return value + 1\n"
            )
        }
    )

    assert result.functions[0].cognitive_complexity == 0


def test_cognitive_complexity_counts_if(service):
    result = service.analyze(
        {
            "module.py": (
                "def example(value):\n"
                "    if value:\n"
                "        return 1\n"
                "    return 0\n"
            )
        }
    )

    assert result.functions[0].cognitive_complexity == 1


def test_nested_if_increases_cognitive_complexity(service):
    result = service.analyze(
        {
            "module.py": (
                "def example(a, b):\n"
                "    if a:\n"
                "        if b:\n"
                "            return 1\n"
                "    return 0\n"
            )
        }
    )

    assert result.functions[0].cognitive_complexity == 3


def test_cognitive_complexity_counts_loop(service):
    result = service.analyze(
        {
            "module.py": (
                "def example(items):\n"
                "    for item in items:\n"
                "        print(item)\n"
            )
        }
    )

    assert result.functions[0].cognitive_complexity == 1


def test_cognitive_complexity_counts_try_handler(service):
    result = service.analyze(
        {
            "module.py": (
                "def example():\n"
                "    try:\n"
                "        int('1')\n"
                "    except ValueError:\n"
                "        return 0\n"
            )
        }
    )

    assert result.functions[0].cognitive_complexity == 1


def test_cognitive_complexity_counts_boolean_operator(service):
    result = service.analyze(
        {
            "module.py": (
                "def example(a, b):\n"
                "    return a and b\n"
            )
        }
    )

    assert result.functions[0].cognitive_complexity == 1


def test_maximum_nesting_depth_simple_function_is_zero(service):
    result = service.analyze(
        {
            "module.py": (
                "def example():\n"
                "    return 1\n"
            )
        }
    )

    assert result.functions[0].max_nesting_depth == 0


def test_maximum_nesting_depth_single_if(service):
    result = service.analyze(
        {
            "module.py": (
                "def example(value):\n"
                "    if value:\n"
                "        return 1\n"
            )
        }
    )

    assert result.functions[0].max_nesting_depth == 1


def test_maximum_nesting_depth_nested_if(service):
    result = service.analyze(
        {
            "module.py": (
                "def example(a, b):\n"
                "    if a:\n"
                "        if b:\n"
                "            return 1\n"
            )
        }
    )

    assert result.functions[0].max_nesting_depth == 2


def test_nested_loop_and_if_depth(service):
    result = service.analyze(
        {
            "module.py": (
                "def example(items):\n"
                "    for item in items:\n"
                "        if item:\n"
                "            while item:\n"
                "                break\n"
            )
        }
    )

    assert result.functions[0].max_nesting_depth == 3


def test_function_line_count(service):
    result = service.analyze(
        {
            "module.py": (
                "def example():\n"
                "    value = 1\n"
                "    return value\n"
            )
        }
    )

    assert result.functions[0].lines == 3


def test_function_parameter_count(service):
    result = service.analyze(
        {
            "module.py": (
                "def example(a, b, c, d):\n"
                "    return a + b + c + d\n"
            )
        }
    )

    assert result.functions[0].parameter_count == 4


def test_keyword_only_parameters_are_counted(service):
    result = service.analyze(
        {
            "module.py": (
                "def example(a, *, b, c):\n"
                "    return a + b + c\n"
            )
        }
    )

    assert result.functions[0].parameter_count == 3


def test_varargs_and_kwargs_are_counted(service):
    result = service.analyze(
        {
            "module.py": (
                "def example(a, *args, **kwargs):\n"
                "    return a\n"
            )
        }
    )

    assert result.functions[0].parameter_count == 3


def test_async_function_is_analyzed(service):
    result = service.analyze(
        {
            "module.py": (
                "async def fetch():\n"
                "    return 1\n"
            )
        }
    )

    assert result.total_functions == 1
    assert result.functions[0].name == "fetch"


def test_class_method_is_analyzed(service):
    result = service.analyze(
        {
            "module.py": (
                "class Example:\n"
                "    def calculate(self, value):\n"
                "        return value + 1\n"
            )
        }
    )

    assert result.total_functions == 1
    assert result.functions[0].qualified_name == "Example.calculate"


def test_nested_function_is_analyzed(service):
    result = service.analyze(
        {
            "module.py": (
                "def outer():\n"
                "    def inner():\n"
                "        return 1\n"
                "    return inner()\n"
            )
        }
    )

    assert result.total_functions == 2
    names = {function.qualified_name for function in result.functions}
    assert names == {"outer", "outer.inner"}


def test_multiple_classes_and_functions_are_analyzed(service):
    result = service.analyze(
        {
            "module.py": (
                "def first():\n"
                "    return 1\n"
                "class Example:\n"
                "    def second(self):\n"
                "        return 2\n"
                "class Another:\n"
                "    def third(self):\n"
                "        return 3\n"
            )
        }
    )

    assert result.total_functions == 3


def test_syntax_error_is_recorded_without_crashing(service):
    result = service.analyze(
        {"broken.py": "def broken(\n    return 1\n"}
    )

    assert result.analyzed_files == 1
    assert result.syntax_error_count == 1
    assert result.file_results[0].syntax_valid is False
    assert result.file_results[0].syntax_error


def test_valid_file_is_still_analyzed_when_another_has_syntax_error(service):
    result = service.analyze(
        {
            "broken.py": "def broken(\n",
            "valid.py": "def example():\n    return 1\n",
        }
    )

    assert result.analyzed_files == 2
    assert result.syntax_error_count == 1
    assert result.total_functions == 1


def test_file_level_metrics_are_calculated(service):
    result = service.analyze(
        {
            "module.py": (
                "def first(value):\n"
                "    if value:\n"
                "        return 1\n"
                "    return 0\n"
                "\n"
                "def second():\n"
                "    return 2\n"
            )
        }
    )

    file_result = result.file_results[0]
    assert file_result.function_count == 2
    assert file_result.maximum_cyclomatic_complexity == 2
    assert file_result.average_cyclomatic_complexity == 1.5


def test_repository_level_metrics_are_calculated(service):
    result = service.analyze(
        {
            "first.py": "def first():\n    return 1\n",
            "second.py": (
                "def second(value):\n"
                "    if value:\n"
                "        return 1\n"
                "    return 0\n"
            ),
        }
    )

    assert result.total_files == 2
    assert result.analyzed_files == 2
    assert result.total_functions == 2
    assert result.average_cyclomatic_complexity == 1.5
    assert result.maximum_cyclomatic_complexity == 2


def test_high_complexity_severity_is_assigned():
    service = CodeComplexityAnalysisService(
        high_cyclomatic_threshold=2,
        critical_cyclomatic_threshold=10,
    )
    result = service.analyze(
        {
            "module.py": (
                "def example(value):\n"
                "    if value:\n"
                "        return 1\n"
                "    return 0\n"
            )
        }
    )

    assert result.functions[0].severity == ComplexitySeverity.HIGH


def test_critical_complexity_severity_is_assigned():
    service = CodeComplexityAnalysisService(
        high_cyclomatic_threshold=2,
        critical_cyclomatic_threshold=3,
    )
    result = service.analyze(
        {
            "module.py": (
                "def example(a, b):\n"
                "    if a:\n"
                "        if b:\n"
                "            return 1\n"
                "    return 0\n"
            )
        }
    )

    assert result.functions[0].severity == ComplexitySeverity.CRITICAL


def test_medium_severity_is_assigned_for_moderate_complexity(service):
    result = service.analyze(
        {
            "module.py": (
                "def example(a, b, c, d):\n"
                "    if a:\n"
                "        return 1\n"
                "    if b:\n"
                "        return 2\n"
                "    if c:\n"
                "        return 3\n"
                "    if d:\n"
                "        return 4\n"
                "    return 0\n"
            )
        }
    )

    assert result.functions[0].severity == ComplexitySeverity.MEDIUM


def test_low_severity_is_assigned_for_simple_function(service):
    result = service.analyze(
        {"module.py": "def example():\n    return 1\n"}
    )

    assert result.functions[0].severity == ComplexitySeverity.LOW


def test_high_complexity_functions_property(service):
    configured = CodeComplexityAnalysisService(
        high_cyclomatic_threshold=2,
        critical_cyclomatic_threshold=3,
    )
    result = configured.analyze(
        {
            "module.py": (
                "def example(value):\n"
                "    if value:\n"
                "        return 1\n"
                "    return 0\n"
            )
        }
    )

    assert len(result.high_complexity_functions) == 1


def test_critical_complexity_functions_property(service):
    configured = CodeComplexityAnalysisService(
        high_cyclomatic_threshold=2,
        critical_cyclomatic_threshold=3,
    )
    result = configured.analyze(
        {
            "module.py": (
                "def example(a, b):\n"
                "    if a:\n"
                "        if b:\n"
                "            return 1\n"
                "    return 0\n"
            )
        }
    )

    assert len(result.critical_complexity_functions) == 1


def test_no_functions_produces_zero_averages(service):
    result = service.analyze({"module.py": "VALUE = 10\n"})

    assert result.total_functions == 0
    assert result.average_cyclomatic_complexity == 0
    assert result.average_cognitive_complexity == 0


def test_functions_are_sorted_by_source_file_order(service):
    result = service.analyze(
        {
            "z.py": "def zed():\n    return 1\n",
            "a.py": "def alpha():\n    return 1\n",
        }
    )

    assert [item.file_path for item in result.file_results] == ["a.py", "z.py"]


def test_duplicate_normalized_paths_are_rejected(service):
    with pytest.raises(CodeComplexityAnalysisError):
        service.analyze(
            {
                "folder\\module.py": "pass",
                "folder/module.py": "pass",
            }
        )


def test_function_model_rejects_invalid_line_range():
    with pytest.raises(ValueError):
        FunctionComplexity(
            file_path="module.py",
            name="example",
            qualified_name="example",
            line=5,
            end_line=4,
            lines=1,
            parameter_count=0,
            cyclomatic_complexity=1,
            cognitive_complexity=0,
            max_nesting_depth=0,
            severity=ComplexitySeverity.LOW,
        )


def test_function_model_rejects_invalid_severity():
    with pytest.raises(TypeError):
        FunctionComplexity(
            file_path="module.py",
            name="example",
            qualified_name="example",
            line=1,
            end_line=1,
            lines=1,
            parameter_count=0,
            cyclomatic_complexity=1,
            cognitive_complexity=0,
            max_nesting_depth=0,
            severity="low",
        )


def test_file_result_rejects_negative_line_count():
    with pytest.raises(ValueError):
        FileComplexityResult(
            file_path="module.py",
            lines_of_code=-1,
            function_count=0,
            average_cyclomatic_complexity=0,
            maximum_cyclomatic_complexity=0,
            average_cognitive_complexity=0,
            maximum_cognitive_complexity=0,
            maximum_nesting_depth=0,
            functions=(),
        )


def test_analysis_result_rejects_inconsistent_file_counts():
    with pytest.raises(ValueError):
        CodeComplexityAnalysisResult(
            total_files=3,
            analyzed_files=1,
            skipped_files=1,
            total_functions=0,
            total_lines_of_code=0,
            average_cyclomatic_complexity=0,
            maximum_cyclomatic_complexity=0,
            average_cognitive_complexity=0,
            maximum_cognitive_complexity=0,
            maximum_nesting_depth=0,
            file_results=(),
            functions=(),
        )


def test_analysis_result_rejects_inconsistent_function_count():
    with pytest.raises(ValueError):
        CodeComplexityAnalysisResult(
            total_files=1,
            analyzed_files=1,
            skipped_files=0,
            total_functions=1,
            total_lines_of_code=1,
            average_cyclomatic_complexity=1,
            maximum_cyclomatic_complexity=1,
            average_cognitive_complexity=0,
            maximum_cognitive_complexity=0,
            maximum_nesting_depth=0,
            file_results=(),
            functions=(),
        )
