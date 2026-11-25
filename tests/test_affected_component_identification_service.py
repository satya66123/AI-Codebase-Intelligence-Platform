import pytest
from types import SimpleNamespace

from app.application.affected_component_identification_service import (
    AffectedComponent,
    AffectedComponentEvidence,
    AffectedComponentIdentificationError,
    AffectedComponentIdentificationResult,
    AffectedComponentIdentificationService,
    ComponentImpactLevel,
)


@pytest.fixture
def service():
    return AffectedComponentIdentificationService()


def entity(name, entity_type, qualified_name, filename, line=1):
    return SimpleNamespace(
        name=name,
        entity_type=entity_type,
        qualified_name=qualified_name,
        filename=filename,
        line=line,
        end_line=line + 5,
    )


def change_finding(
    affected_file="app/service.py",
    affected_entity="service.run",
    relationship_type="call",
    changed_target="core.calculate",
    line=12,
    reason="Calls changed function.",
):
    return SimpleNamespace(
        source_file="app/core.py",
        affected_file=affected_file,
        affected_entity=affected_entity,
        relationship_type=relationship_type,
        changed_target=changed_target,
        line=line,
        reason=reason,
    )


def indirect_finding(
    affected_file="app/ui.py",
    affected_entity="ui.render",
    impact_type="call",
    changed_target="core.calculate",
    depth=2,
    relationship_types=("call", "import"),
    reason="Reached through dependency path.",
):
    return SimpleNamespace(
        changed_target=changed_target,
        affected_file=affected_file,
        affected_entity=affected_entity,
        impact_type=impact_type,
        depth=depth,
        relationship_types=relationship_types,
        path=("core.calculate", "service.run", "ui.render"),
        reason=reason,
    )


def test_identify_returns_empty_result_when_no_changes_or_findings(service):
    result = service.identify()

    assert result.total_components == 0
    assert result.total_affected_files == 0
    assert result.components == ()
    assert result.has_affected_components is False
    assert result.healthy is True


def test_identify_explicit_changed_file(service):
    result = service.identify(changed_files=("app/main.py",))

    assert result.total_components == 1
    component = result.components[0]
    assert component.file_path == "app/main.py"
    assert component.entity_name == "app/main.py"
    assert component.entity_type == "file"
    assert component.impact_level is ComponentImpactLevel.DIRECT


def test_identify_explicit_changed_entity(service):
    code_entities = (entity("run", "function", "app.service.run", "app/service.py"),)

    result = service.identify(
        changed_entities=("app.service.run",),
        code_entities=code_entities,
    )

    assert result.total_components == 1
    component = result.components[0]
    assert component.entity_name == "app.service.run"
    assert component.entity_type == "function"
    assert component.impact_level is ComponentImpactLevel.DIRECT


def test_identify_changed_entity_by_simple_name(service):
    code_entities = (entity("run", "function", "app.service.run", "app/service.py"),)

    result = service.identify(changed_entities=("run",), code_entities=code_entities)

    assert result.total_components == 1
    assert result.components[0].entity_name == "app.service.run"


def test_identify_unmapped_changed_entity(service):
    result = service.identify(changed_entities=("missing.function",))

    assert result.total_components == 0
    assert result.healthy is False
    assert "missing.function" in result.unmapped_findings[0]


def test_identify_maps_change_finding_to_function(service):
    code_entities = (entity("run", "function", "service.run", "app/service.py"),)
    result = service.identify(
        code_entities=code_entities,
        change_impact_result=SimpleNamespace(findings=(change_finding(),)),
    )

    assert result.total_components == 1
    component = result.components[0]
    assert component.entity_name == "service.run"
    assert component.impact_level is ComponentImpactLevel.DIRECT
    assert "call" in component.impact_types


def test_identify_falls_back_to_file_when_entity_is_not_found(service):
    result = service.identify(
        change_impact_result=SimpleNamespace(
            findings=(change_finding(affected_entity="unknown.function"),)
        )
    )

    assert result.total_components == 1
    assert result.components[0].entity_type == "file"
    assert result.components[0].file_path == "app/service.py"


def test_identify_maps_change_finding_to_module_entity(service):
    module = entity("service", "module", "service", "app/service.py")
    result = service.identify(
        code_entities=(module,),
        change_impact_result=SimpleNamespace(
            findings=(change_finding(affected_entity=None),)
        ),
    )

    assert result.components[0].entity_type == "module"


def test_identify_maps_indirect_finding(service):
    code_entities = (entity("render", "function", "ui.render", "app/ui.py"),)
    result = service.identify(
        code_entities=code_entities,
        impact_analysis_result=SimpleNamespace(findings=(indirect_finding(),)),
    )

    assert result.total_components == 1
    component = result.components[0]
    assert component.impact_level is ComponentImpactLevel.INDIRECT
    assert component.impact_depth == 2


def test_identify_depth_one_as_direct_impact(service):
    result = service.identify(
        impact_analysis_result=SimpleNamespace(
            findings=(indirect_finding(depth=1),)
        )
    )

    assert result.direct_components == 1
    assert result.indirect_components == 0


def test_identify_depth_greater_than_one_as_indirect_impact(service):
    result = service.identify(
        impact_analysis_result=SimpleNamespace(
            findings=(indirect_finding(depth=3),)
        )
    )

    assert result.indirect_components == 1
    assert result.components[0].impact_depth == 3


def test_identify_deduplicates_same_component_from_multiple_sources(service):
    code_entities = (entity("run", "function", "service.run", "app/service.py"),)
    direct = change_finding(affected_entity="service.run")
    indirect = indirect_finding(
        affected_file="app/service.py",
        affected_entity="service.run",
        depth=2,
    )

    result = service.identify(
        code_entities=code_entities,
        change_impact_result=SimpleNamespace(findings=(direct,)),
        impact_analysis_result=SimpleNamespace(findings=(indirect,)),
    )

    assert result.total_components == 1
    assert result.direct_components == 1
    assert result.indirect_components == 0
    assert len(result.components[0].evidence) == 2


def test_identify_combines_multiple_changed_targets(service):
    findings = (
        change_finding(changed_target="core.first"),
        change_finding(changed_target="core.second"),
    )
    result = service.identify(
        change_impact_result=SimpleNamespace(findings=findings)
    )

    assert result.total_components == 1
    assert result.components[0].changed_targets == ("core.first", "core.second")


def test_identify_collects_relationship_types(service):
    findings = (
        change_finding(relationship_type="call"),
        change_finding(relationship_type="import"),
    )
    result = service.identify(
        change_impact_result=SimpleNamespace(findings=findings)
    )

    assert result.components[0].impact_types == ("call", "import")


def test_identify_preserves_evidence_details(service):
    finding = change_finding(line=27, reason="A caller references the changed function.")
    result = service.identify(
        change_impact_result=SimpleNamespace(findings=(finding,))
    )

    evidence = result.components[0].evidence[0]
    assert evidence.source == "change_impact"
    assert evidence.line == 27
    assert evidence.reason == "A caller references the changed function."


def test_identify_reports_affected_files_deterministically(service):
    findings = (
        change_finding(affected_file="z/module.py"),
        change_finding(affected_file="a/module.py"),
    )
    result = service.identify(
        change_impact_result=SimpleNamespace(findings=findings)
    )

    assert result.affected_files == ("a/module.py", "z/module.py")


def test_identify_counts_direct_and_indirect_components(service):
    findings = (
        indirect_finding(affected_file="a.py", affected_entity=None, depth=1),
        indirect_finding(affected_file="b.py", affected_entity=None, depth=2),
        indirect_finding(affected_file="c.py", affected_entity=None, depth=3),
    )
    result = service.identify(
        impact_analysis_result=SimpleNamespace(findings=findings)
    )

    assert result.total_components == 3
    assert result.direct_components == 1
    assert result.indirect_components == 2


def test_identify_exposes_direct_and_indirect_component_properties(service):
    result = service.identify(
        impact_analysis_result=SimpleNamespace(
            findings=(
                indirect_finding(affected_file="direct.py", depth=1),
                indirect_finding(affected_file="indirect.py", depth=2),
            )
        )
    )

    assert len(result.directly_affected_components) == 1
    assert len(result.indirectly_affected_components) == 1


def test_identify_considers_data_flow_result_statistics(service):
    data_flow = SimpleNamespace(
        analyzed=True,
        edges=(object(), object(), object()),
    )
    result = service.identify(data_flow_results=(data_flow,))

    assert result.data_flow_files_considered == 1
    assert result.data_flow_edges_considered == 3


def test_identify_ignores_unanalyzed_data_flow_results(service):
    data_flow = SimpleNamespace(analyzed=False, edges=(object(),))
    result = service.identify(data_flow_results=(data_flow,))

    assert result.data_flow_files_considered == 0
    assert result.data_flow_edges_considered == 0


def test_identify_combines_explicit_file_and_finding_for_same_file(service):
    result = service.identify(
        changed_files=("app/service.py",),
        change_impact_result=SimpleNamespace(
            findings=(change_finding(affected_file="app/service.py"),)
        ),
    )

    assert result.total_components == 1
    assert result.direct_components == 1
    assert len(result.components[0].evidence) == 2


def test_identify_uses_module_entity_for_explicit_changed_file(service):
    module = entity("service", "module", "service", "app/service.py")
    result = service.identify(
        changed_files=("app/service.py",),
        code_entities=(module,),
    )

    assert result.components[0].entity_type == "module"
    assert result.components[0].entity_name == "service"


def test_identify_is_deterministic(service):
    findings = (
        change_finding(affected_file="z.py", changed_target="z.target"),
        change_finding(affected_file="a.py", changed_target="a.target"),
    )
    first = service.identify(
        change_impact_result=SimpleNamespace(findings=findings)
    )
    second = service.identify(
        change_impact_result=SimpleNamespace(findings=findings)
    )

    assert first == second


@pytest.mark.parametrize(
    "kwargs",
    [
        {"changed_files": None},
        {"changed_files": "app.py"},
        {"changed_files": {"app.py"}},
        {"changed_files": ("",)},
        {"changed_files": ("app.py", "app.py")},
        {"changed_entities": None},
        {"changed_entities": "function"},
        {"changed_entities": {"function"}},
        {"changed_entities": ("",)},
        {"code_entities": None},
        {"code_entities": "entity"},
        {"data_flow_results": None},
        {"data_flow_results": {"result"}},
    ],
)
def test_identify_rejects_invalid_collections(service, kwargs):
    with pytest.raises(AffectedComponentIdentificationError):
        service.identify(**kwargs)


def test_identify_rejects_malformed_change_impact_result(service):
    with pytest.raises(AffectedComponentIdentificationError):
        service.identify(change_impact_result=object())


def test_identify_rejects_non_collection_findings(service):
    with pytest.raises(AffectedComponentIdentificationError):
        service.identify(
            change_impact_result=SimpleNamespace(findings={object()})
        )


def test_identify_rejects_malformed_impact_analysis_result(service):
    with pytest.raises(AffectedComponentIdentificationError):
        service.identify(impact_analysis_result=object())


def test_identify_rejects_finding_missing_required_attributes(service):
    with pytest.raises(AffectedComponentIdentificationError):
        service.identify(
            change_impact_result=SimpleNamespace(findings=(object(),))
        )


def test_identify_skips_finding_without_affected_file_and_reports_it(service):
    finding = SimpleNamespace(
        affected_file="",
        relationship_type="call",
        changed_target="core.run",
    )
    result = service.identify(
        change_impact_result=SimpleNamespace(findings=(finding,))
    )

    assert result.total_components == 0
    assert result.healthy is False
    assert result.unmapped_findings


def test_identify_skips_invalid_impact_depth(service):
    finding = indirect_finding(depth=0)
    result = service.identify(
        impact_analysis_result=SimpleNamespace(findings=(finding,))
    )

    assert result.total_components == 0
    assert result.healthy is False


def test_identify_component_model_rejects_empty_file_path():
    with pytest.raises(AffectedComponentIdentificationError):
        AffectedComponent(
            file_path="",
            entity_name="run",
            entity_type="function",
            impact_level=ComponentImpactLevel.DIRECT,
            impact_depth=1,
            impact_types=(),
            changed_targets=(),
            relationship_types=(),
            evidence=(),
        )


def test_evidence_model_rejects_empty_source():
    with pytest.raises(AffectedComponentIdentificationError):
        AffectedComponentEvidence(
            source="",
            relationship_type="call",
            changed_target="main.run",
            reason="A call edge exists.",
        )


@pytest.mark.parametrize("line", [-1, True, "2"])
def test_evidence_model_rejects_invalid_line(line):
    with pytest.raises(AffectedComponentIdentificationError):
        AffectedComponentEvidence(
            source="change_impact",
            relationship_type="call",
            changed_target="main.run",
            reason="A call edge exists.",
            line=line,
        )


def test_result_model_rejects_inconsistent_component_count():
    with pytest.raises(AffectedComponentIdentificationError):
        AffectedComponentIdentificationResult(
            total_components=1,
            total_affected_files=0,
            direct_components=0,
            indirect_components=0,
            components=(),
            affected_files=(),
            unmapped_findings=(),
        )


def test_result_model_rejects_inconsistent_impact_counts():
    with pytest.raises(AffectedComponentIdentificationError):
        AffectedComponentIdentificationResult(
            total_components=1,
            total_affected_files=0,
            direct_components=1,
            indirect_components=1,
            components=(),
            affected_files=(),
            unmapped_findings=(),
        )


def test_result_exposes_impact_count_aliases(service):
    result = service.identify(changed_files=("app.py",))

    assert result.direct_impact_count == 1
    assert result.indirect_impact_count == 0


def test_change_finding_with_invalid_line_uses_zero(service):
    finding = change_finding(line="not-a-line")
    result = service.identify(
        change_impact_result=SimpleNamespace(findings=(finding,))
    )

    assert result.components[0].evidence[0].line == 0


def test_indirect_finding_without_relationship_types_uses_impact_type(service):
    finding = indirect_finding(relationship_types=())
    result = service.identify(
        impact_analysis_result=SimpleNamespace(findings=(finding,))
    )

    assert result.components[0].relationship_types == ("call",)


def test_multiple_evidence_records_are_sorted(service):
    findings = (
        change_finding(changed_target="z.target", line=20),
        change_finding(changed_target="a.target", line=10),
    )
    result = service.identify(
        change_impact_result=SimpleNamespace(findings=findings)
    )

    evidence = result.components[0].evidence
    assert tuple(item.line for item in evidence) == (10, 20)
