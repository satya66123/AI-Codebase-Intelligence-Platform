
import pytest

from appy.application.call_graph_service import (
    CallGraphResult,
    CallRecord,
)
from appy.application.code_entity_extractor import CodeEntity
from appy.application.dependency_analyzer import DependencyRecord
from appy.application.direct_indirect_impact_detection_service import (
    DirectIndirectImpactDetectionError,
    DirectIndirectImpactDetectionService,
    DirectIndirectImpactAnalysisResult,
    DirectIndirectImpactFinding,
    ImpactPath,
)


@pytest.fixture
def service():
    return DirectIndirectImpactDetectionService()


def make_entity(name, filename, entity_type="function", parent=None):
    return CodeEntity(
        name=name.rsplit(".", 1)[-1],
        entity_type=entity_type,
        qualified_name=name,
        filename=filename,
        line=1,
        end_line=10,
        parent=parent,
        docstring=None,
    )


def make_graph(filename, caller, callee, line=10, caller_type="function"):
    record = CallRecord(
        filename=filename,
        caller=caller,
        caller_type=caller_type,
        callee=callee,
        call_type="function",
        line=line,
    )
    return CallGraphResult(
        filename=filename,
        calls=(record,),
        total_calls=1,
    )


def make_dependency(source, imported, line=3):
    return DependencyRecord(
        source_file=source,
        imported_module=imported,
        imported_name=None,
        alias=None,
        dependency_type="internal",
        line=line,
        is_relative=False,
    )


def test_direct_function_call_impact(service):
    entities = (
        make_entity("billing.calculate", "billing.py"),
        make_entity("checkout.process", "checkout.py"),
    )
    graph = make_graph(
        "checkout.py",
        "checkout.process",
        "calculate",
    )

    result = service.analyze(
        changed_entities=("billing.calculate",),
        code_entities=entities,
        call_graphs=(graph,),
    )

    assert isinstance(result, DirectIndirectImpactAnalysisResult)
    assert result.has_impact
    assert result.direct_impact_count == 1
    assert result.indirect_impact_count == 0
    assert result.findings[0].affected_file == "checkout.py"
    assert result.findings[0].impact_type == "direct"
    assert result.findings[0].depth == 1


def test_indirect_function_call_impact(service):
    entities = (
        make_entity("billing.calculate", "billing.py"),
        make_entity("checkout.process", "checkout.py"),
        make_entity("api.submit", "api.py"),
    )

    graphs = (
        make_graph(
            "checkout.py",
            "checkout.process",
            "calculate",
        ),
        make_graph(
            "api.py",
            "api.submit",
            "process",
        ),
    )

    result = service.analyze(
        changed_entities=("billing.calculate",),
        code_entities=entities,
        call_graphs=graphs,
    )

    assert result.direct_impact_count == 1
    assert result.indirect_impact_count == 1

    indirect = [
        item for item in result.findings
        if item.impact_type == "indirect"
    ][0]

    assert indirect.affected_file == "api.py"
    assert indirect.depth == 2
    assert indirect.path.nodes == (
        "billing.calculate",
        "checkout.process",
        "api.submit",
    )


def test_direct_import_impact(service):
    result = service.analyze(
        changed_files=("billing.py",),
        dependencies=(make_dependency("checkout.py", "billing"),),
    )

    assert result.direct_impact_count == 1
    assert result.indirect_impact_count == 0
    assert result.affected_files == ("checkout.py",)
    assert result.findings[0].relationship_types == ("import",)


def test_indirect_import_impact(service):
    dependencies = (
        make_dependency("checkout.py", "billing"),
        make_dependency("api.py", "checkout"),
    )

    result = service.analyze(
        changed_files=("billing.py",),
        dependencies=dependencies,
    )

    assert result.direct_impact_count == 1
    assert result.indirect_impact_count == 1
    assert result.total_impact_count == 2
    assert result.maximum_impact_depth == 2
    assert result.affected_files == ("api.py", "checkout.py")


def test_mixed_call_and_import_impact(service):
    entities = (
        make_entity("billing.calculate", "billing.py"),
        make_entity("checkout.process", "checkout.py"),
    )
    graph = make_graph(
        "checkout.py",
        "checkout.process",
        "calculate",
    )
    dependency = make_dependency("api.py", "checkout")

    result = service.analyze(
        changed_entities=("billing.calculate",),
        code_entities=entities,
        call_graphs=(graph,),
        dependencies=(dependency,),
    )

    assert result.direct_impact_count == 1
    assert result.indirect_impact_count == 1
    assert result.total_impact_count == 2
    assert result.maximum_impact_depth == 2
    assert result.affected_files == ("api.py", "checkout.py")

    indirect = result.indirect_findings[0]
    assert indirect.affected_file == "api.py"
    assert indirect.relationship_types == (
        "function_call",
        "import",
    )


def test_method_call_impact(service):
    entities = (
        make_entity(
            "storage.Store.save",
            "storage.py",
            "method",
            "storage.Store",
        ),
        make_entity(
            "controller.Controller.update",
            "controller.py",
            "method",
            "controller.Controller",
        ),
    )

    graph = make_graph(
        "controller.py",
        "controller.Controller.update",
        "save",
        caller_type="method",
    )

    result = service.analyze(
        changed_entities=("storage.Store.save",),
        code_entities=entities,
        call_graphs=(graph,),
    )

    assert result.direct_impact_count == 1
    assert result.findings[0].relationship_types == ("method_call",)


def test_recursive_call_does_not_loop_forever(service):
    entities = (
        make_entity("billing.calculate", "billing.py"),
        make_entity("checkout.process", "checkout.py"),
    )

    graphs = (
        make_graph("checkout.py", "checkout.process", "calculate"),
        make_graph("billing.py", "billing.calculate", "process"),
    )

    result = service.analyze(
        changed_entities=("billing.calculate",),
        code_entities=entities,
        call_graphs=graphs,
    )

    assert result.has_impact
    assert result.maximum_impact_depth == 1


def test_cycle_in_import_graph_does_not_loop_forever(service):
    dependencies = (
        make_dependency("checkout.py", "billing"),
        make_dependency("billing.py", "checkout"),
    )

    result = service.analyze(
        changed_files=("billing.py",),
        dependencies=dependencies,
    )

    assert result.direct_impact_count == 1
    assert result.indirect_impact_count == 0


def test_max_depth_limits_traversal(service):
    entities = (
        make_entity("billing.calculate", "billing.py"),
        make_entity("checkout.process", "checkout.py"),
        make_entity("api.submit", "api.py"),
        make_entity("web.route", "web.py"),
    )

    graphs = (
        make_graph("checkout.py", "checkout.process", "calculate"),
        make_graph("api.py", "api.submit", "process"),
        make_graph("web.py", "web.route", "submit"),
    )

    result = service.analyze(
        changed_entities=("billing.calculate",),
        code_entities=entities,
        call_graphs=graphs,
        max_depth=2,
    )

    assert result.maximum_impact_depth == 2
    assert "web.py" not in result.affected_files


def test_no_impact_returns_healthy_result(service):
    result = service.analyze(
        changed_files=("billing.py",),
    )

    assert not result.has_impact
    assert result.healthy
    assert result.findings == ()
    assert result.maximum_impact_depth == 0


def test_external_dependencies_are_ignored(service):
    dependency = DependencyRecord(
        source_file="checkout.py",
        imported_module="requests",
        imported_name=None,
        alias=None,
        dependency_type="external",
        line=1,
        is_relative=False,
    )

    result = service.analyze(
        changed_files=("requests.py",),
        dependencies=(dependency,),
    )

    assert not result.has_impact


def test_unresolved_dependencies_are_ignored(service):
    dependency = DependencyRecord(
        source_file="checkout.py",
        imported_module=None,
        imported_name=None,
        alias=None,
        dependency_type="unresolved",
        line=1,
        is_relative=True,
    )

    result = service.analyze(
        changed_files=("billing.py",),
        dependencies=(dependency,),
    )

    assert not result.has_impact


def test_duplicate_call_graph_edges_are_deduplicated(service):
    entities = (
        make_entity("billing.calculate", "billing.py"),
        make_entity("checkout.process", "checkout.py"),
    )

    graph = CallGraphResult(
        filename="checkout.py",
        calls=(
            CallRecord(
                "checkout.py",
                "checkout.process",
                "function",
                "calculate",
                "function",
                10,
            ),
            CallRecord(
                "checkout.py",
                "checkout.process",
                "function",
                "calculate",
                "function",
                10,
            ),
        ),
        total_calls=2,
    )

    result = service.analyze(
        changed_entities=("billing.calculate",),
        code_entities=entities,
        call_graphs=(graph,),
    )

    assert result.direct_impact_count == 1


def test_duplicate_changed_targets_are_removed(service):
    result = service.analyze(
        changed_files=("billing.py", "billing.py"),
    )

    assert result.changed_targets == ("billing", "billing.py")


def test_windows_paths_are_normalized(service):
    result = service.analyze(
        changed_files=("appy\\services\\billing.py",),
        dependencies=(
            make_dependency(
                "appy\\services\\checkout.py",
                "appy.services.billing",
            ),
        ),
    )

    assert result.affected_files == (
        "appy/services/checkout.py",
    )


def test_nested_package_import_is_resolved(service):
    dependencies = (
        make_dependency(
            "appy/services/checkout.py",
            "appy.services.billing",
        ),
    )

    result = service.analyze(
        changed_files=("appy/services/billing.py",),
        dependencies=dependencies,
    )

    assert result.affected_files == (
        "appy/services/checkout.py",
    )


def test_result_direct_and_indirect_properties(service):
    entities = (
        make_entity("billing.calculate", "billing.py"),
        make_entity("checkout.process", "checkout.py"),
        make_entity("api.submit", "api.py"),
    )
    graphs = (
        make_graph("checkout.py", "checkout.process", "calculate"),
        make_graph("api.py", "api.submit", "process"),
    )

    result = service.analyze(
        changed_entities=("billing.calculate",),
        code_entities=entities,
        call_graphs=graphs,
    )

    assert result.has_direct_impact
    assert result.has_indirect_impact
    assert len(result.direct_findings) == 1
    assert len(result.indirect_findings) == 1


def test_result_relationship_path_is_preserved(service):
    entities = (
        make_entity("billing.calculate", "billing.py"),
        make_entity("checkout.process", "checkout.py"),
    )
    graph = make_graph(
        "checkout.py",
        "checkout.process",
        "calculate",
    )

    result = service.analyze(
        changed_entities=("billing.calculate",),
        code_entities=entities,
        call_graphs=(graph,),
    )

    path = result.findings[0].path
    assert isinstance(path, ImpactPath)
    assert path.nodes == (
        "billing.calculate",
        "checkout.process",
    )
    assert path.relationship_types == ("function_call",)
    assert path.depth == 1


def test_analysis_counts_relationships(service):
    dependencies = (
        make_dependency("checkout.py", "billing"),
        make_dependency("api.py", "checkout"),
    )

    result = service.analyze(
        changed_files=("billing.py",),
        dependencies=dependencies,
    )

    assert result.total_relationships == 2
    assert result.total_graph_nodes >= 3


def test_file_entity_bridge_is_not_reported_as_impact(service):
    entities = (
        make_entity("billing.calculate", "billing.py"),
        make_entity("checkout.process", "checkout.py"),
    )
    graph = make_graph(
        "checkout.py",
        "checkout.process",
        "calculate",
    )

    result = service.analyze(
        changed_entities=("billing.calculate",),
        code_entities=entities,
        call_graphs=(graph,),
    )

    assert result.total_impact_count == 1
    assert all(
        finding.relationship_types != ("contains",)
        for finding in result.findings
    )


def test_entity_change_traverses_through_its_file_to_importers(service):
    entities = (
        make_entity("billing.calculate", "billing.py"),
        make_entity("checkout.process", "checkout.py"),
    )
    graph = make_graph(
        "checkout.py",
        "checkout.process",
        "calculate",
    )
    dependency = make_dependency("api.py", "checkout")

    result = service.analyze(
        changed_entities=("billing.calculate",),
        code_entities=entities,
        call_graphs=(graph,),
        dependencies=(dependency,),
    )

    assert result.affected_files == ("api.py", "checkout.py")
    assert result.direct_impact_count == 1
    assert result.indirect_impact_count == 1
    assert result.maximum_impact_depth == 2


def test_import_only_chain_has_correct_paths(service):
    dependencies = (
        make_dependency("checkout.py", "billing"),
        make_dependency("api.py", "checkout"),
    )

    result = service.analyze(
        changed_files=("billing.py",),
        dependencies=dependencies,
    )

    indirect = result.indirect_findings[0]

    assert indirect.path.nodes == (
        "billing.py",
        "checkout.py",
        "api.py",
    )
    assert indirect.relationship_types == ("import", "import")
    assert indirect.depth == 2


def test_analyze_requires_changed_target(service):
    with pytest.raises(DirectIndirectImpactDetectionError):
        service.analyze()


@pytest.mark.parametrize("max_depth", [0, -1, True, "2", None])
def test_invalid_max_depth_is_rejected(service, max_depth):
    with pytest.raises(DirectIndirectImpactDetectionError):
        service.analyze(
            changed_files=("billing.py",),
            max_depth=max_depth,
        )


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
def test_invalid_changed_files_are_rejected(service, changed_files):
    with pytest.raises(DirectIndirectImpactDetectionError):
        service.analyze(changed_files=changed_files)


@pytest.mark.parametrize(
    "changed_entities",
    [
        None,
        "billing.calculate",
        {"billing.calculate"},
    ],
)
def test_invalid_changed_entities_are_rejected(
    service,
    changed_entities,
):
    with pytest.raises(DirectIndirectImpactDetectionError):
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
        "appy/../billing.py",
        "appy//billing.py",
        "./billing.py",
        "C:\\project\\billing.py",
    ],
)
def test_invalid_file_paths_are_rejected(service, path):
    with pytest.raises(DirectIndirectImpactDetectionError):
        service.analyze(changed_files=(path,))


@pytest.mark.parametrize(
    "argument",
    [
        "code_entities",
        "call_graphs",
        "dependencies",
    ],
)
def test_invalid_record_types_are_rejected(service, argument):
    with pytest.raises(DirectIndirectImpactDetectionError):
        service.analyze(
            changed_files=("billing.py",),
            **{argument: (object(),)},
        )


@pytest.mark.parametrize(
    "argument",
    [
        "code_entities",
        "call_graphs",
        "dependencies",
    ],
)
def test_unordered_record_collections_are_rejected(
    service,
    argument,
):
    with pytest.raises(DirectIndirectImpactDetectionError):
        service.analyze(
            changed_files=("billing.py",),
            **{argument: {object()}},
        )


def test_impact_path_rejects_single_node():
    with pytest.raises(DirectIndirectImpactDetectionError):
        ImpactPath(
            nodes=("billing.calculate",),
            relationship_types=(),
        )


def test_impact_path_rejects_mismatched_relationships():
    with pytest.raises(DirectIndirectImpactDetectionError):
        ImpactPath(
            nodes=("billing.calculate", "checkout.process"),
            relationship_types=("function_call", "import"),
        )


def test_finding_rejects_invalid_impact_type():
    path = ImpactPath(
        nodes=("billing.calculate", "checkout.process"),
        relationship_types=("function_call",),
    )

    with pytest.raises(DirectIndirectImpactDetectionError):
        DirectIndirectImpactFinding(
            changed_target="billing.calculate",
            affected_file="checkout.py",
            affected_entity="checkout.process",
            impact_type="unknown",
            depth=1,
            relationship_types=("function_call",),
            path=path,
            reason="Test",
        )


def test_finding_rejects_inconsistent_depth():
    path = ImpactPath(
        nodes=("billing.calculate", "checkout.process"),
        relationship_types=("function_call",),
    )

    with pytest.raises(DirectIndirectImpactDetectionError):
        DirectIndirectImpactFinding(
            changed_target="billing.calculate",
            affected_file="checkout.py",
            affected_entity="checkout.process",
            impact_type="direct",
            depth=2,
            relationship_types=("function_call",),
            path=path,
            reason="Test",
        )


def test_result_rejects_inconsistent_total_count():
    with pytest.raises(DirectIndirectImpactDetectionError):
        DirectIndirectImpactAnalysisResult(
            changed_targets=("billing.py",),
            total_graph_nodes=1,
            total_relationships=0,
            direct_impact_count=0,
            indirect_impact_count=0,
            total_impact_count=1,
            affected_files=(),
            findings=(),
            maximum_impact_depth=0,
        )


def test_result_rejects_negative_counts():
    with pytest.raises(DirectIndirectImpactDetectionError):
        DirectIndirectImpactAnalysisResult(
            changed_targets=(),
            total_graph_nodes=-1,
            total_relationships=0,
            direct_impact_count=0,
            indirect_impact_count=0,
            total_impact_count=0,
            affected_files=(),
            findings=(),
            maximum_impact_depth=0,
        )
