
import pytest

from app.application.code_quality_analysis_service import (
    CodeQualityAnalysisError,
    CodeQualityAnalysisResult,
    CodeQualityAnalysisService,
    CodeQualityFinding,
    FileQualityResult,
    QualityCategory,
    QualitySeverity,
)


@pytest.fixture
def service():
    return CodeQualityAnalysisService()


def test_service_initializes_with_default_thresholds(service):
    assert service.max_line_length == 100
    assert service.max_function_lines == 50
    assert service.max_class_lines == 300
    assert service.max_function_parameters == 5
    assert service.max_complexity == 10


@pytest.mark.parametrize(
    "kwargs",
    [
        {"max_line_length": 0},
        {"max_function_lines": 0},
        {"max_class_lines": 0},
        {"max_function_parameters": 0},
        {"max_complexity": 0},
        {"max_line_length": True},
    ],
)
def test_invalid_thresholds_are_rejected(kwargs):
    with pytest.raises(CodeQualityAnalysisError):
        CodeQualityAnalysisService(**kwargs)


def test_empty_repository_returns_valid_empty_result(service):
    result = service.analyze({})

    assert isinstance(result, CodeQualityAnalysisResult)
    assert result.total_files == 0
    assert result.analyzed_files == 0
    assert result.skipped_files == 0
    assert result.total_lines_of_code == 0
    assert result.score == 100.0
    assert result.findings == ()
    assert result.healthy is True


def test_analyze_requires_mapping(service):
    with pytest.raises(CodeQualityAnalysisError):
        service.analyze("not a mapping")


@pytest.mark.parametrize(
    "source_files",
    [
        {"module.py": None},
        {"module.py": 123},
        {"module.py": b"print('hello')"},
    ],
)
def test_source_content_must_be_string(service, source_files):
    with pytest.raises(CodeQualityAnalysisError):
        service.analyze(source_files)


@pytest.mark.parametrize(
    "path",
    [
        "",
        "../outside.py",
        "/absolute/module.py",
        "./module.py",
        "folder//module.py",
        "C:\\outside\\module.py",
    ],
)
def test_invalid_source_paths_are_rejected(service, path):
    with pytest.raises(CodeQualityAnalysisError):
        service.analyze({path: "pass"})


def test_source_files_are_analyzed_in_sorted_order(service):
    result = service.analyze(
        {
            "z_module.py": '"""Z module."""\n',
            "a_module.py": '"""A module."""\n',
        }
    )

    assert [item.file_path for item in result.file_results] == [
        "a_module.py",
        "z_module.py",
    ]


def test_non_python_files_are_skipped(service):
    result = service.analyze(
        {
            "README.md": "# Project",
            "settings.json": "{}",
            "module.py": '"""Module."""\n',
        }
    )

    assert result.total_files == 3
    assert result.analyzed_files == 1
    assert result.skipped_files == 2
    assert result.file_results[0].file_path == "module.py"


def test_python_file_is_analyzed(service):
    result = service.analyze(
        {"module.py": '"""Module documentation."""\nvalue = 10\n'}
    )

    assert result.analyzed_files == 1
    assert result.file_results[0].file_path == "module.py"


def test_lines_of_code_excludes_blank_lines(service):
    result = service.analyze(
        {"module.py": '"""Module."""\n\nvalue = 10\n\n'}
    )

    assert result.total_lines_of_code == 2


def test_missing_module_docstring_is_reported(service):
    result = service.analyze({"module.py": "value = 10\n"})

    codes = {finding.code for finding in result.findings}
    assert "MISSING_MODULE_DOCSTRING" in codes


def test_module_docstring_is_accepted(service):
    result = service.analyze(
        {"module.py": '"""Module documentation."""\nvalue = 10\n'}
    )

    codes = {finding.code for finding in result.findings}
    assert "MISSING_MODULE_DOCSTRING" not in codes


def test_missing_function_docstring_is_reported(service):
    result = service.analyze(
        {
            "module.py": (
                '"""Module."""\n'
                "def calculate(value):\n"
                "    return value + 1\n"
            )
        }
    )

    assert "MISSING_FUNCTION_DOCSTRING" in {
        finding.code for finding in result.findings
    }


def test_function_docstring_is_accepted(service):
    result = service.analyze(
        {
            "module.py": (
                '"""Module."""\n'
                "def calculate(value):\n"
                '    """Calculate a value."""\n'
                "    return value + 1\n"
            )
        }
    )

    assert "MISSING_FUNCTION_DOCSTRING" not in {
        finding.code for finding in result.findings
    }


def test_missing_class_docstring_is_reported(service):
    result = service.analyze(
        {
            "module.py": (
                '"""Module."""\n'
                "class Example:\n"
                "    pass\n"
            )
        }
    )

    assert "MISSING_CLASS_DOCSTRING" in {
        finding.code for finding in result.findings
    }


def test_class_docstring_is_accepted(service):
    result = service.analyze(
        {
            "module.py": (
                '"""Module."""\n'
                "class Example:\n"
                '    """Example class."""\n'
                "    pass\n"
            )
        }
    )

    assert "MISSING_CLASS_DOCSTRING" not in {
        finding.code for finding in result.findings
    }


def test_long_line_is_reported():
    service = CodeQualityAnalysisService(max_line_length=20)
    result = service.analyze(
        {"module.py": '"""Module."""\nvalue = "this line is too long"\n'}
    )

    assert "LINE_TOO_LONG" in {
        finding.code for finding in result.findings
    }


def test_line_within_limit_is_not_reported():
    service = CodeQualityAnalysisService(max_line_length=100)
    result = service.analyze(
        {"module.py": '"""Module."""\nvalue = 10\n'}
    )

    assert "LINE_TOO_LONG" not in {
        finding.code for finding in result.findings
    }


def test_trailing_whitespace_is_reported(service):
    result = service.analyze(
        {"module.py": '"""Module."""\nvalue = 10  \n'}
    )

    assert "TRAILING_WHITESPACE" in {
        finding.code for finding in result.findings
    }


def test_tab_indentation_is_reported(service):
    result = service.analyze(
        {"module.py": '"""Module."""\ndef example():\n\treturn 1\n'}
    )

    assert "TAB_INDENTATION" in {
        finding.code for finding in result.findings
    }


@pytest.mark.parametrize("marker", ["TODO", "FIXME", "XXX"])
def test_development_markers_are_reported(service, marker):
    result = service.analyze(
        {"module.py": f'"""Module."""\n# {marker}: finish this\n'}
    )

    assert "DEVELOPMENT_MARKER" in {
        finding.code for finding in result.findings
    }


def test_function_with_too_many_parameters_is_reported():
    service = CodeQualityAnalysisService(max_function_parameters=3)
    result = service.analyze(
        {
            "module.py": (
                '"""Module."""\n'
                "def calculate(a, b, c, d):\n"
                '    """Calculate."""\n'
                "    return a + b + c + d\n"
            )
        }
    )

    assert "TOO_MANY_PARAMETERS" in {
        finding.code for finding in result.findings
    }


def test_function_with_allowed_parameters_is_not_reported():
    service = CodeQualityAnalysisService(max_function_parameters=4)
    result = service.analyze(
        {
            "module.py": (
                '"""Module."""\n'
                "def calculate(a, b, c, d):\n"
                '    """Calculate."""\n'
                "    return a + b + c + d\n"
            )
        }
    )

    assert "TOO_MANY_PARAMETERS" not in {
        finding.code for finding in result.findings
    }


def test_keyword_only_parameters_are_counted():
    service = CodeQualityAnalysisService(max_function_parameters=2)
    result = service.analyze(
        {
            "module.py": (
                '"""Module."""\n'
                "def calculate(a, *, b, c):\n"
                '    """Calculate."""\n'
                "    return a + b + c\n"
            )
        }
    )

    assert "TOO_MANY_PARAMETERS" in {
        finding.code for finding in result.findings
    }


def test_varargs_and_kwargs_are_counted():
    service = CodeQualityAnalysisService(max_function_parameters=2)
    result = service.analyze(
        {
            "module.py": (
                '"""Module."""\n'
                "def calculate(a, *args, **kwargs):\n"
                '    """Calculate."""\n'
                "    return a\n"
            )
        }
    )

    assert "TOO_MANY_PARAMETERS" in {
        finding.code for finding in result.findings
    }


def test_high_cyclomatic_complexity_is_reported():
    service = CodeQualityAnalysisService(max_complexity=2)
    result = service.analyze(
        {
            "module.py": (
                '"""Module."""\n'
                "def calculate(value):\n"
                '    """Calculate."""\n'
                "    if value > 0:\n"
                "        if value > 10:\n"
                "            return 1\n"
                "        else:\n"
                "            return 2\n"
                "    return 0\n"
            )
        }
    )

    assert "HIGH_CYCLOMATIC_COMPLEXITY" in {
        finding.code for finding in result.findings
    }


def test_low_complexity_function_is_not_reported():
    service = CodeQualityAnalysisService(max_complexity=10)
    result = service.analyze(
        {
            "module.py": (
                '"""Module."""\n'
                "def calculate(value):\n"
                '    """Calculate."""\n'
                "    return value + 1\n"
            )
        }
    )

    assert "HIGH_CYCLOMATIC_COMPLEXITY" not in {
        finding.code for finding in result.findings
    }


def test_long_function_is_reported():
    service = CodeQualityAnalysisService(max_function_lines=3)
    body = "\n".join(f"    value_{i} = {i}" for i in range(5))
    source = (
        '"""Module."""\n'
        "def example():\n"
        '    """Example."""\n'
        f"{body}\n"
        "    return value_4\n"
    )

    result = service.analyze({"module.py": source})

    assert "FUNCTION_TOO_LONG" in {
        finding.code for finding in result.findings
    }


def test_short_function_is_not_reported():
    service = CodeQualityAnalysisService(max_function_lines=20)
    result = service.analyze(
        {
            "module.py": (
                '"""Module."""\n'
                "def example():\n"
                '    """Example."""\n'
                "    return 1\n"
            )
        }
    )

    assert "FUNCTION_TOO_LONG" not in {
        finding.code for finding in result.findings
    }


def test_long_class_is_reported():
    service = CodeQualityAnalysisService(max_class_lines=4)
    body = "\n".join(f"    value_{i} = {i}" for i in range(6))
    source = (
        '"""Module."""\n'
        "class Example:\n"
        '    """Example."""\n'
        f"{body}\n"
    )

    result = service.analyze({"module.py": source})

    assert "CLASS_TOO_LONG" in {
        finding.code for finding in result.findings
    }


def test_broad_exception_handler_is_reported(service):
    result = service.analyze(
        {
            "module.py": (
                '"""Module."""\n'
                "def run():\n"
                '    """Run."""\n'
                "    try:\n"
                "        return int('1')\n"
                "    except Exception:\n"
                "        return None\n"
            )
        }
    )

    assert "BROAD_EXCEPTION_HANDLER" in {
        finding.code for finding in result.findings
    }


def test_specific_exception_handler_is_not_broad(service):
    result = service.analyze(
        {
            "module.py": (
                '"""Module."""\n'
                "def run():\n"
                '    """Run."""\n'
                "    try:\n"
                "        return int('1')\n"
                "    except ValueError:\n"
                "        return None\n"
            )
        }
    )

    assert "BROAD_EXCEPTION_HANDLER" not in {
        finding.code for finding in result.findings
    }


def test_empty_exception_handler_is_reported(service):
    result = service.analyze(
        {
            "module.py": (
                '"""Module."""\n'
                "def run():\n"
                '    """Run."""\n'
                "    try:\n"
                "        return int('1')\n"
                "    except ValueError:\n"
                "        pass\n"
            )
        }
    )

    assert "EMPTY_EXCEPTION_HANDLER" in {
        finding.code for finding in result.findings
    }


def test_invalid_python_syntax_is_reported(service):
    result = service.analyze(
        {"module.py": "def broken(\n    return 1\n"}
    )

    assert result.analyzed_files == 1
    assert "PYTHON_SYNTAX_ERROR" in {
        finding.code for finding in result.findings
    }


def test_invalid_syntax_does_not_crash_other_files(service):
    result = service.analyze(
        {
            "broken.py": "def broken(\n",
            "valid.py": '"""Valid module."""\nvalue = 1\n',
        }
    )

    assert result.analyzed_files == 2
    assert len(result.file_results) == 2
    assert any(
        finding.code == "PYTHON_SYNTAX_ERROR"
        for finding in result.findings
    )


def test_function_naming_convention_is_checked(service):
    result = service.analyze(
        {
            "module.py": (
                '"""Module."""\n'
                "def CalculateValue():\n"
                '    """Calculate."""\n'
                "    return 1\n"
            )
        }
    )

    assert "FUNCTION_NAMING_CONVENTION" in {
        finding.code for finding in result.findings
    }


def test_private_function_naming_is_not_flagged(service):
    result = service.analyze(
        {
            "module.py": (
                '"""Module."""\n'
                "def _calculate_value():\n"
                '    """Calculate."""\n'
                "    return 1\n"
            )
        }
    )

    assert "FUNCTION_NAMING_CONVENTION" not in {
        finding.code for finding in result.findings
    }


def test_class_naming_convention_is_checked(service):
    result = service.analyze(
        {
            "module.py": (
                '"""Module."""\n'
                "class example_class:\n"
                '    """Example."""\n'
                "    pass\n"
            )
        }
    )

    assert "CLASS_NAMING_CONVENTION" in {
        finding.code for finding in result.findings
    }


def test_valid_class_name_is_not_flagged(service):
    result = service.analyze(
        {
            "module.py": (
                '"""Module."""\n'
                "class ExampleClass:\n"
                '    """Example."""\n'
                "    pass\n"
            )
        }
    )

    assert "CLASS_NAMING_CONVENTION" not in {
        finding.code for finding in result.findings
    }


def test_finding_contains_file_line_and_symbol(service):
    result = service.analyze(
        {
            "module.py": (
                '"""Module."""\n'
                "def CalculateValue():\n"
                '    """Calculate."""\n'
                "    return 1\n"
            )
        }
    )

    finding = next(
        item
        for item in result.findings
        if item.code == "FUNCTION_NAMING_CONVENTION"
    )

    assert finding.file_path == "module.py"
    assert finding.line == 2
    assert finding.symbol == "CalculateValue"


def test_repository_score_is_between_zero_and_100(service):
    result = service.analyze(
        {
            "module.py": (
                "def CalculateValue(a, b, c, d, e, f):\n"
                "    return a + b + c + d + e + f\n"
            )
        }
    )

    assert 0.0 <= result.score <= 100.0


def test_clean_module_has_full_score(service):
    result = service.analyze(
        {
            "module.py": (
                '"""Module documentation."""\n'
                "def calculate(value):\n"
                '    """Calculate a value."""\n'
                "    return value + 1\n"
            )
        }
    )

    assert result.score == 100.0


def test_findings_are_aggregated_across_files(service):
    result = service.analyze(
        {
            "first.py": "value = 1\n",
            "second.py": "value = 2\n",
        }
    )

    assert result.total_files == 2
    assert result.analyzed_files == 2
    assert len(result.findings) >= 2


def test_result_exposes_severity_counts(service):
    result = service.analyze(
        {
            "module.py": (
                "def example():\n"
                "    try:\n"
                "        pass\n"
                "    except Exception:\n"
                "        pass\n"
            )
        }
    )

    assert result.info_count >= 0
    assert result.warning_count >= 0
    assert result.error_count >= 0
    assert (
        result.error_count + result.warning_count + result.info_count
        == len(result.findings)
    )


def test_result_exposes_category_counts(service):
    result = service.analyze(
        {"module.py": "value = 1\n"}
    )

    counts = result.findings_by_category
    assert isinstance(counts, dict)
    assert "documentation" in counts


def test_result_exposes_severity_mapping(service):
    result = service.analyze(
        {"module.py": "value = 1\n"}
    )

    assert isinstance(result.findings_by_severity, dict)


def test_non_python_only_repository_has_full_score(service):
    result = service.analyze(
        {
            "README.md": "# Documentation",
            "settings.json": "{}",
        }
    )

    assert result.total_files == 2
    assert result.analyzed_files == 0
    assert result.skipped_files == 2
    assert result.score == 100.0


def test_entities_must_be_sequence(service):
    with pytest.raises(CodeQualityAnalysisError):
        service.analyze({}, entities="invalid")


def test_entities_can_be_supplied_without_changing_analysis(service):
    class ExampleEntity:
        name = "calculate"
        entity_type = "function"
        qualified_name = "module.calculate"
        filename = "module.py"
        line = 2
        end_line = 4
        parent = None
        docstring = "Calculate."

    result = service.analyze(
        {
            "module.py": (
                '"""Module."""\n'
                "def calculate(value):\n"
                '    """Calculate."""\n'
                "    return value + 1\n"
            )
        },
        entities=[ExampleEntity()],
    )

    assert result.analyzed_files == 1
    assert result.score == 100.0


def test_finding_model_rejects_empty_code():
    with pytest.raises(ValueError):
        CodeQualityFinding(
            code="",
            message="Problem",
            file_path="module.py",
            severity=QualitySeverity.WARNING,
            category=QualityCategory.STYLE,
        )


def test_finding_model_rejects_invalid_severity():
    with pytest.raises(TypeError):
        CodeQualityFinding(
            code="ISSUE",
            message="Problem",
            file_path="module.py",
            severity="warning",
            category=QualityCategory.STYLE,
        )


def test_finding_model_rejects_invalid_line():
    with pytest.raises(ValueError):
        CodeQualityFinding(
            code="ISSUE",
            message="Problem",
            file_path="module.py",
            severity=QualitySeverity.WARNING,
            category=QualityCategory.STYLE,
            line=0,
        )


def test_file_result_rejects_invalid_score():
    with pytest.raises(ValueError):
        FileQualityResult(
            file_path="module.py",
            score=101,
            lines_of_code=1,
            findings=(),
        )


def test_file_result_rejects_negative_line_count():
    with pytest.raises(ValueError):
        FileQualityResult(
            file_path="module.py",
            score=100,
            lines_of_code=-1,
            findings=(),
        )


def test_analysis_result_rejects_inconsistent_file_counts():
    with pytest.raises(ValueError):
        CodeQualityAnalysisResult(
            total_files=3,
            analyzed_files=1,
            skipped_files=1,
            total_lines_of_code=10,
            score=100,
            file_results=(),
            findings=(),
        )


def test_analysis_result_rejects_invalid_score():
    with pytest.raises(ValueError):
        CodeQualityAnalysisResult(
            total_files=0,
            analyzed_files=0,
            skipped_files=0,
            total_lines_of_code=0,
            score=101,
            file_results=(),
            findings=(),
        )


def test_async_function_is_analyzed(service):
    result = service.analyze(
        {
            "module.py": (
                '"""Module."""\n'
                "async def fetch_data():\n"
                '    """Fetch data."""\n'
                "    return 1\n"
            )
        }
    )

    assert result.analyzed_files == 1
    assert "MISSING_FUNCTION_DOCSTRING" not in {
        finding.code for finding in result.findings
    }


def test_nested_function_is_analyzed(service):
    result = service.analyze(
        {
            "module.py": (
                '"""Module."""\n'
                "def outer():\n"
                '    """Outer."""\n'
                "    def inner():\n"
                "        return 1\n"
                "    return inner()\n"
            )
        }
    )

    assert any(
        finding.code == "MISSING_FUNCTION_DOCSTRING"
        and finding.symbol == "inner"
        for finding in result.findings
    )


def test_boolean_expression_increases_complexity():
    service = CodeQualityAnalysisService(max_complexity=1)
    result = service.analyze(
        {
            "module.py": (
                '"""Module."""\n'
                "def check(a, b):\n"
                '    """Check."""\n'
                "    return a and b\n"
            )
        }
    )

    assert "HIGH_CYCLOMATIC_COMPLEXITY" in {
        finding.code for finding in result.findings
    }


def test_if_expression_increases_complexity():
    service = CodeQualityAnalysisService(max_complexity=1)
    result = service.analyze(
        {
            "module.py": (
                '"""Module."""\n'
                "def check(value):\n"
                '    """Check."""\n'
                "    return 1 if value else 0\n"
            )
        }
    )

    assert "HIGH_CYCLOMATIC_COMPLEXITY" in {
        finding.code for finding in result.findings
    }


def test_result_healthy_when_no_error_severity_findings(service):
    result = service.analyze(
        {"module.py": "value = 1\n"}
    )

    assert result.healthy is True
