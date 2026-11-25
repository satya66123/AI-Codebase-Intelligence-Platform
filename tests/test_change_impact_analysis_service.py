
import pytest

from app.application.call_graph_service import (
    CallGraphResult,
    CallRecord,
)
from app.application.code_entity_extractor import CodeEntity
from app.application.dependency_analyzer import DependencyRecord
from app.application.change_impact_analysis_service import (
    ChangeImpactAnalysisError,
    ChangeImpactAnalysisResult,
    ChangeImpactAnalysisService,
    ChangeImpactFinding,
    ChangeImpactTarget,
)


@pytest.fixture
def service():
    return ChangeImpactAnalysisService()


@pytest.fixture
def changed_function():
    return CodeEntity(
        name="calculate",
        entity_type="function",
        qualified_name="billing.calculate",
        filename="billing.py",
        line=1,
        end_line=5,
        parent="billing",
        docstring=None,
    )


@pytest.fixture
def call_graph():
    calls = (
        CallRecord(
            filename="checkout.py",
            caller="checkout.process_order",
            caller_type="function",
            callee="calculate",
            call_type="function",
            line=12,
        ),
        CallRecord(
            filename="reports.py",
            caller="reports.generate",
            caller_type="function",
            callee="format_report",
            call_type="function",
            line=20,
        ),
    )

    return CallGraphResult(
        filename="checkout.py",
        calls=calls,
        total_calls=2,
    )


def test_analyze_changed_entity_finds_callers(
    service,
    changed_function,
    call_graph,
):
    result = service.analyze(
        changed_entities=("billing.calculate",),
        code_entities=(changed_function,),
        call_graphs=(call_graph,),
    )

    assert isinstance(result, ChangeImpactAnalysisResult)
    assert result.has_impact
    assert result.affected_files == ("checkout.py",)
    assert result.total_impact_findings == 1

    finding = result.findings[0]
    assert finding.affected_file == "checkout.py"
    assert finding.affected_entity == "checkout.process_order"
    assert finding.changed_target == "billing.calculate"
    assert finding.relationship_type == "function_call"
    assert finding.line == 12


def test_analyze_changed_file_finds_importers(service):
    dependency = DependencyRecord(
        source_file="checkout.py",
        imported_module="billing",
        imported_name=None,
        alias=None,
        dependency_type="internal",
        line=3,
        is_relative=False,
    )

    result = service.analyze(
        changed_files=("billing.py",),
        dependencies=(dependency,),
    )

    assert result.has_impact
    assert result.affected_files == ("checkout.py",)
    assert result.findings[0].relationship_type == "import"
    assert result.findings[0].changed_target == "billing.py"


def test_analyze_changed_entity_finds_importers(service):
    dependency = DependencyRecord(
        source_file="checkout.py",
        imported_module="billing",
        imported_name="calculate",
        alias=None,
        dependency_type="internal",
        line=4,
        is_relative=False,
    )

    result = service.analyze(
        changed_entities=("billing.calculate",),
        dependencies=(dependency,),
    )

    assert result.has_impact
    assert result.affected_files == ("checkout.py",)
    assert result.findings[0].changed_target == "billing.calculate"


def test_analyze_changed_file_and_entity_together(
    service,
    changed_function,
    call_graph,
):
    dependency = DependencyRecord(
        source_file="checkout.py",
        imported_module="billing",
        imported_name="calculate",
        alias=None,
        dependency_type="internal",
        line=3,
        is_relative=False,
    )

    result = service.analyze(
        changed_files=("billing.py",),
        changed_entities=("billing.calculate",),
        code_entities=(changed_function,),
        call_graphs=(call_graph,),
        dependencies=(dependency,),
    )

    assert result.has_impact
    assert result.affected_files == ("checkout.py",)
    assert result.total_impact_findings == 3


def test_analyze_returns_no_impact_when_no_relationships_exist(service):
    result = service.analyze(
        changed_files=("billing.py",),
    )

    assert not result.has_impact
    assert result.healthy
    assert result.affected_files == ()
    assert result.findings == ()
    assert result.total_impact_findings == 0


def test_analyze_does_not_report_calls_inside_changed_file(
    service,
    changed_function,
    call_graph,
):
    result = service.analyze(
        changed_files=("checkout.py",),
        changed_entities=("billing.calculate",),
        code_entities=(changed_function,),
        call_graphs=(call_graph,),
    )

    assert not result.has_impact


def test_analyze_ignores_unrelated_calls(service, call_graph):
    result = service.analyze(
        changed_entities=("billing.calculate",),
        call_graphs=(call_graph,),
    )

    assert not result.has_impact


def test_analyze_detects_method_call_relationship(service):
    entity = CodeEntity(
        name="save",
        entity_type="method",
        qualified_name="storage.Store.save",
        filename="storage.py",
        line=5,
        end_line=9,
        parent="storage.Store",
        docstring=None,
    )

    graph = CallGraphResult(
        filename="controller.py",
        calls=(
            CallRecord(
                filename="controller.py",
                caller="controller.Controller.update",
                caller_type="method",
                callee="save",
                call_type="attribute",
                line=18,
            ),
        ),
        total_calls=1,
    )

    result = service.analyze(
        changed_entities=("storage.Store.save",),
        code_entities=(entity,),
        call_graphs=(graph,),
    )

    assert result.has_impact
    assert result.findings[0].relationship_type == "method_call"
    assert result.findings[0].affected_entity == (
        "controller.Controller.update"
    )


def test_analyze_supports_nested_changed_file_paths(service):
    dependency = DependencyRecord(
        source_file="app/services/checkout.py",
        imported_module="app.services.billing",
        imported_name=None,
        alias=None,
        dependency_type="internal",
        line=2,
        is_relative=False,
    )

    result = service.analyze(
        changed_files=("app/services/billing.py",),
        dependencies=(dependency,),
    )

    assert result.affected_files == ("app/services/checkout.py",)


def test_analyze_normalizes_windows_file_paths(service):
    dependency = DependencyRecord(
        source_file="app\\services\\checkout.py",
        imported_module="app.services.billing",
        imported_name=None,
        alias=None,
        dependency_type="internal",
        line=2,
        is_relative=False,
    )

    result = service.analyze(
        changed_files=("app\\services\\billing.py",),
        dependencies=(dependency,),
    )

    assert result.affected_files == ("app/services/checkout.py",)


def test_analyze_deduplicates_changed_targets(service):
    result = service.analyze(
        changed_files=("billing.py", "billing.py"),
    )

    assert result.changed_targets == (
        ChangeImpactTarget("file", "billing.py"),
    )


def test_analyze_deduplicates_duplicate_dependencies(service):
    dependency = DependencyRecord(
        source_file="checkout.py",
        imported_module="billing",
        imported_name=None,
        alias=None,
        dependency_type="internal",
        line=3,
        is_relative=False,
    )

    result = service.analyze(
        changed_files=("billing.py",),
        dependencies=(dependency, dependency),
    )

    assert result.total_dependencies_analyzed == 2
    assert result.total_impact_findings == 1


def test_analyze_orders_findings_deterministically(service):
    dependencies = (
        DependencyRecord(
            source_file="zebra.py",
            imported_module="billing",
            imported_name=None,
            alias=None,
            dependency_type="internal",
            line=9,
            is_relative=False,
        ),
        DependencyRecord(
            source_file="alpha.py",
            imported_module="billing",
            imported_name=None,
            alias=None,
            dependency_type="internal",
            line=4,
            is_relative=False,
        ),
    )

    result = service.analyze(
        changed_files=("billing.py",),
        dependencies=dependencies,
    )

    assert result.affected_files == ("alpha.py", "zebra.py")
    assert result.findings[0].affected_file == "alpha.py"


def test_result_relationship_summary(service):
    dependencies = (
        DependencyRecord(
            source_file="checkout.py",
            imported_module="billing",
            imported_name=None,
            alias=None,
            dependency_type="internal",
            line=3,
            is_relative=False,
        ),
    )

    result = service.analyze(
        changed_files=("billing.py",),
        dependencies=dependencies,
    )

    assert result.findings_by_relationship == {"import": 1}


def test_result_affected_file_count(service):
    dependencies = (
        DependencyRecord(
            source_file="checkout.py",
            imported_module="billing",
            imported_name=None,
            alias=None,
            dependency_type="internal",
            line=3,
            is_relative=False,
        ),
        DependencyRecord(
            source_file="reports.py",
            imported_module="billing",
            imported_name=None,
            alias=None,
            dependency_type="internal",
            line=7,
            is_relative=False,
        ),
    )

    result = service.analyze(
        changed_files=("billing.py",),
        dependencies=dependencies,
    )

    assert result.affected_file_count == 2


def test_total_files_analyzed_counts_unique_files(service):
    entity = CodeEntity(
        name="calculate",
        entity_type="function",
        qualified_name="billing.calculate",
        filename="billing.py",
        line=1,
        end_line=5,
        parent="billing",
        docstring=None,
    )

    graph = CallGraphResult(
        filename="billing.py",
        calls=(),
        total_calls=0,
    )

    dependency = DependencyRecord(
        source_file="billing.py",
        imported_module="math",
        imported_name=None,
        alias=None,
        dependency_type="standard_library",
        line=1,
        is_relative=False,
    )

    result = service.analyze(
        changed_files=("billing.py",),
        code_entities=(entity,),
        call_graphs=(graph,),
        dependencies=(dependency,),
    )

    assert result.total_files_analyzed == 1
    assert result.total_entities_analyzed == 1
    assert result.total_calls_analyzed == 0
    assert result.total_dependencies_analyzed == 1


def test_analyze_rejects_empty_targets(service):
    with pytest.raises(
        ChangeImpactAnalysisError,
        match="At least one changed file or entity",
    ):
        service.analyze()


@pytest.mark.parametrize(
    "changed_files",
    [
        None,
        "billing.py",
        b"billing.py",
        {"billing.py"},
        {"billing.py": True},
    ],
)
def test_analyze_rejects_invalid_changed_files(
    service,
    changed_files,
):
    with pytest.raises(ChangeImpactAnalysisError):
        service.analyze(changed_files=changed_files)


@pytest.mark.parametrize(
    "changed_entities",
    [
        None,
        "billing.calculate",
        b"billing.calculate",
        {"billing.calculate"},
        {"billing.calculate": True},
    ],
)
def test_analyze_rejects_invalid_changed_entities(
    service,
    changed_entities,
):
    with pytest.raises(ChangeImpactAnalysisError):
        service.analyze(
            changed_files=("billing.py",),
            changed_entities=changed_entities,
        )


@pytest.mark.parametrize(
    "path",
    [
        "",
        " ",
        "/billing.py",
        "../billing.py",
        "app/../billing.py",
        "app//billing.py",
        "./billing.py",
        "C:\\project\\billing.py",
    ],
)
def test_analyze_rejects_invalid_changed_file_paths(service, path):
    with pytest.raises(ChangeImpactAnalysisError):
        service.analyze(changed_files=(path,))


@pytest.mark.parametrize(
    "entity",
    [
        "",
        " ",
        None,
        123,
    ],
)
def test_analyze_rejects_invalid_entity_targets(service, entity):
    with pytest.raises(ChangeImpactAnalysisError):
        service.analyze(changed_entities=(entity,))


@pytest.mark.parametrize(
    "argument, value",
    [
        ("code_entities", (object(),)),
        ("call_graphs", (object(),)),
        ("dependencies", (object(),)),
    ],
)
def test_analyze_rejects_invalid_record_types(
    service,
    argument,
    value,
):
    with pytest.raises(ChangeImpactAnalysisError):
        service.analyze(
            changed_files=("billing.py",),
            **{argument: value},
        )


@pytest.mark.parametrize(
    "argument",
    [
        "code_entities",
        "call_graphs",
        "dependencies",
    ],
)
def test_analyze_rejects_unordered_record_collections(
    service,
    argument,
):
    with pytest.raises(ChangeImpactAnalysisError):
        service.analyze(
            changed_files=("billing.py",),
            **{argument: {object()}},
        )


def test_change_impact_target_rejects_invalid_type():
    with pytest.raises(ChangeImpactAnalysisError):
        ChangeImpactTarget("directory", "app")


def test_change_impact_target_normalizes_file_path():
    target = ChangeImpactTarget(
        "file",
        "app\\services\\billing.py",
    )

    assert target.value == "app/services/billing.py"


def test_change_impact_target_rejects_empty_value():
    with pytest.raises(ChangeImpactAnalysisError):
        ChangeImpactTarget("entity", " ")


def test_finding_rejects_empty_relationship_type():
    with pytest.raises(ChangeImpactAnalysisError):
        ChangeImpactFinding(
            source_file="checkout.py",
            affected_file="checkout.py",
            relationship_type="",
            changed_target="billing.calculate",
            affected_entity="checkout.process",
            line=10,
            reason="A call was found.",
        )


@pytest.mark.parametrize("line", [-1, True, "10"])
def test_finding_rejects_invalid_line(line):
    with pytest.raises(ChangeImpactAnalysisError):
        ChangeImpactFinding(
            source_file="checkout.py",
            affected_file="checkout.py",
            relationship_type="function_call",
            changed_target="billing.calculate",
            affected_entity="checkout.process",
            line=line,
            reason="A call was found.",
        )


def test_result_rejects_inconsistent_finding_count():
    with pytest.raises(ChangeImpactAnalysisError):
        ChangeImpactAnalysisResult(
            changed_targets=(),
            total_files_analyzed=0,
            total_entities_analyzed=0,
            total_calls_analyzed=0,
            total_dependencies_analyzed=0,
            total_impact_findings=1,
            affected_files=(),
            findings=(),
        )


def test_result_rejects_negative_analysis_count():
    with pytest.raises(ChangeImpactAnalysisError):
        ChangeImpactAnalysisResult(
            changed_targets=(),
            total_files_analyzed=-1,
            total_entities_analyzed=0,
            total_calls_analyzed=0,
            total_dependencies_analyzed=0,
            total_impact_findings=0,
            affected_files=(),
            findings=(),
        )


def test_result_rejects_non_tuple_findings():
    with pytest.raises(ChangeImpactAnalysisError):
        ChangeImpactAnalysisResult(
            changed_targets=(),
            total_files_analyzed=0,
            total_entities_analyzed=0,
            total_calls_analyzed=0,
            total_dependencies_analyzed=0,
            total_impact_findings=0,
            affected_files=(),
            findings=[],
        )
