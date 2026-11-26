
import pytest

from appy.application.call_graph_service import (
    CallGraphError,
    CallGraphResult,
    CallGraphService,
)
from appy.application.python_language_parser import (
    PythonLanguageParser,
)


@pytest.fixture
def service():
    return CallGraphService()


@pytest.fixture
def parser():
    return PythonLanguageParser()


def test_analyze_returns_call_graph_result(service, parser):
    parsed = parser.parse("print('Hello')", "appy.py")

    result = service.analyze(parsed)

    assert isinstance(result, CallGraphResult)


def test_extract_simple_function_call(service, parser):
    result = service.analyze(
        parser.parse("print('Hello')", "appy.py")
    )

    assert result.total_calls == 1
    assert result.calls[0].callee == "print"
    assert result.calls[0].call_type == "function"


def test_extract_call_inside_function(service, parser):
    source = """
def greet():
    print("Hello")
"""

    result = service.analyze(parser.parse(source, "appy.py"))

    call = result.calls[0]

    assert call.caller == "appy.greet"
    assert call.caller_type == "function"
    assert call.callee == "print"


def test_extract_method_call(service, parser):
    source = """
class Employee:
    def work(self):
        self.save()
"""

    result = service.analyze(parser.parse(source, "models.py"))

    call = result.calls[0]

    assert call.caller == "models.Employee.work"
    assert call.caller_type == "method"
    assert call.callee == "self.save"
    assert call.call_type == "attribute"


def test_extract_attribute_call(service, parser):
    result = service.analyze(
        parser.parse("service.process()", "appy.py")
    )

    assert result.calls[0].callee == "service.process"
    assert result.calls[0].call_type == "attribute"


def test_extract_nested_function_calls(service, parser):
    source = """
def outer():
    inner()
"""

    result = service.analyze(parser.parse(source, "appy.py"))

    assert result.calls[0].caller == "appy.outer"
    assert result.calls[0].callee == "inner"


def test_extract_nested_calls_in_arguments(service, parser):
    source = "print(str(len(values)))"

    result = service.analyze(parser.parse(source, "appy.py"))

    callees = {call.callee for call in result.calls}

    assert callees == {"print", "str", "len"}
    assert result.total_calls == 3


def test_extract_calls_in_nested_functions(service, parser):
    source = """
def outer():
    def inner():
        save()
    load()
"""

    result = service.analyze(parser.parse(source, "appy.py"))

    calls_by_callee = {
        call.callee: call.caller
        for call in result.calls
    }

    assert calls_by_callee["save"] == "appy.outer.inner"
    assert calls_by_callee["load"] == "appy.outer"


def test_extract_async_function_calls(service, parser):
    source = """
async def fetch():
    await load_data()
"""

    result = service.analyze(parser.parse(source, "appy.py"))

    assert result.calls[0].caller == "appy.fetch"
    assert result.calls[0].callee == "load_data"


def test_extract_class_body_call(service, parser):
    source = """
class Example:
    register()
"""

    result = service.analyze(parser.parse(source, "appy.py"))

    assert result.calls[0].caller == "appy.Example"
    assert result.calls[0].caller_type == "class"


def test_extract_dynamic_call(service, parser):
    source = "get_handler()()"

    result = service.analyze(parser.parse(source, "appy.py"))

    assert result.total_calls == 2
    assert any(
        call.call_type == "dynamic"
        for call in result.calls
    )


def test_preserve_filename_and_line(service, parser):
    source = """
def run():
    execute()
"""

    result = service.analyze(
        parser.parse(source, "services.py")
    )

    call = result.calls[0]

    assert call.filename == "services.py"
    assert call.line == 3


def test_no_calls_returns_empty_result(service, parser):
    result = service.analyze(
        parser.parse("value = 10", "appy.py")
    )

    assert result.calls == ()
    assert result.total_calls == 0


def test_reject_invalid_input(service):
    with pytest.raises(
        CallGraphError,
        match="ParsedSource",
    ):
        service.analyze("invalid input")
