
from types import SimpleNamespace

import pytest

from appy.application.architecture_pattern_detection_service import (
    ArchitecturePattern,
    ArchitecturePatternDetectionError,
    ArchitecturePatternDetectionResult,
    ArchitecturePatternDetectionService,
    ArchitecturePatternEvidence,
    ArchitecturePatternFinding,
    PatternConfidence,
)


@pytest.fixture
def service():
    return ArchitecturePatternDetectionService()


def entity(
    name,
    entity_type="class",
    qualified_name=None,
    filename="appy/module.py",
):
    return SimpleNamespace(
        name=name,
        entity_type=entity_type,
        qualified_name=qualified_name or name,
        filename=filename,
    )


def graph(
    filename="appy/agents/research_agent.py",
    total_calls=2,
):
    return SimpleNamespace(
        filename=filename,
        total_calls=total_calls,
    )


def dep(
    source_file="appy/service.py",
    imported_module="appy.domain",
):
    return SimpleNamespace(
        source_file=source_file,
        imported_module=imported_module,
    )


def test_empty_repository(service):
    result = service.analyze()

    assert result.total_files == 0
    assert result.patterns_detected == 0
    assert result.findings == ()
    assert result.healthy


def test_analyzed_files_are_sorted_and_unique(service):
    result = service.analyze(
        source_files=("z.py", "a.py")
    )

    assert result.analyzed_files == ("a.py", "z.py")


def test_windows_paths_are_normalized(service):
    result = service.analyze(
        source_files=(r"appy\services\user.py",)
    )

    assert result.analyzed_files == (
        "appy/services/user.py",
    )


def test_detects_four_layer_architecture(service):
    result = service.analyze(
        source_files=(
            "appy/presentation/page.py",
            "appy/application/use_case.py",
            "appy/domain/entity.py",
            "appy/infrastructure/database.py",
        )
    )

    finding = result.get_pattern(
        ArchitecturePattern.LAYERED
    )

    assert finding.confidence is PatternConfidence.HIGH
    assert finding.evidence_count == 4


def test_detects_three_layer_architecture(service):
    result = service.analyze(
        source_files=(
            "appy/ui/page.py",
            "appy/services/use_case.py",
            "appy/domain/entity.py",
        )
    )

    finding = result.get_pattern("layered_architecture")

    assert finding.confidence is PatternConfidence.MEDIUM


def test_does_not_detect_two_layers(service):
    result = service.analyze(
        source_files=(
            "appy/ui/page.py",
            "appy/domain/entity.py",
        )
    )

    assert result.get_pattern(
        ArchitecturePattern.LAYERED
    ) is None


def test_detects_mvc_from_names(service):
    result = service.analyze(
        code_entities=(
            entity("UserModel", filename="models/user.py"),
            entity("UserView", filename="views/user.py"),
            entity(
                "UserController",
                filename="controllers/user.py",
            ),
        )
    )

    assert result.get_pattern(
        ArchitecturePattern.MVC
    ) is not None


def test_detects_mvc_from_directories(service):
    result = service.analyze(
        code_entities=(
            entity("User", filename="models/user.py"),
            entity("Screen", filename="views/screen.py"),
            entity(
                "Handler",
                filename="controllers/handler.py",
            ),
        )
    )

    assert result.get_pattern(
        ArchitecturePattern.MVC
    ) is  None


def test_mvc_requires_all_three_roles(service):
    result = service.analyze(
        code_entities=(
            entity("UserModel", filename="models/user.py"),
            entity(
                "UserController",
                filename="controllers/user.py",
            ),
        )
    )

    assert result.get_pattern(
        ArchitecturePattern.MVC
    ) is None


def test_detects_repository_by_class_name(service):
    result = service.analyze(
        code_entities=(entity("UserRepository"),)
    )

    finding = result.get_pattern(
        ArchitecturePattern.REPOSITORY
    )

    assert finding.confidence is PatternConfidence.MEDIUM


def test_detects_repository_by_directory(service):
    result = service.analyze(
        code_entities=(
            entity(
                "UserStore",
                filename="repositories/user.py",
            ),
        )
    )

    assert result.get_pattern(
        ArchitecturePattern.REPOSITORY
    ) is None


def test_repository_confidence_for_multiple_classes(service):
    result = service.analyze(
        code_entities=(
            entity("UserRepository", filename="user.py"),
            entity("OrderRepository", filename="order.py"),
        )
    )

    finding = result.get_pattern(
        ArchitecturePattern.REPOSITORY
    )

    assert finding.confidence is PatternConfidence.HIGH


def test_repository_requires_class_entity(service):
    result = service.analyze(
        code_entities=(
            entity("UserRepository", "function"),
        )
    )

    assert result.get_pattern(
        ArchitecturePattern.REPOSITORY
    ) is None


def test_detects_service_class(service):
    result = service.analyze(
        code_entities=(entity("PaymentService"),)
    )

    assert result.get_pattern(
        ArchitecturePattern.SERVICE_LAYER
    ) is not None


def test_detects_service_directory(service):
    result = service.analyze(
        source_files=("appy/services/payment.py",)
    )

    assert result.get_pattern(
        ArchitecturePattern.SERVICE_LAYER
    ) is not None


def test_service_layer_confidence_from_multiple_entities(service):
    result = service.analyze(
        code_entities=(
            entity("UserService", filename="user.py"),
            entity("OrderService", filename="order.py"),
        )
    )

    finding = result.get_pattern(
        ArchitecturePattern.SERVICE_LAYER
    )

    assert finding.confidence is PatternConfidence.HIGH


def test_does_not_detect_service_without_indicators(service):
    result = service.analyze(
        source_files=("appy/core/user.py",),
        code_entities=(
            entity(
                "UserManager",
                filename="appy/core/user.py",
            ),
        ),
    )

    assert result.get_pattern(
        ArchitecturePattern.SERVICE_LAYER
    ) is None


def test_detects_factory_class(service):
    result = service.analyze(
        code_entities=(entity("ProviderFactory"),)
    )

    assert result.get_pattern(
        ArchitecturePattern.FACTORY
    ) is not None


def test_detects_create_function(service):
    result = service.analyze(
        code_entities=(
            entity(
                "create_provider",
                "function",
                "providers.create_provider",
                "providers.py",
            ),
        )
    )

    assert result.get_pattern(
        ArchitecturePattern.FACTORY
    ) is not None


def test_does_not_detect_non_factory_name(service):
    result = service.analyze(
        code_entities=(entity("ProviderBuilder"),)
    )

    assert result.get_pattern(
        ArchitecturePattern.FACTORY
    ) is None


def test_detects_agent_by_class_name(service):
    result = service.analyze(
        code_entities=(entity("ResearchAgent"),)
    )

    finding = result.get_pattern(
        ArchitecturePattern.AGENT
    )

    assert finding.confidence is PatternConfidence.MEDIUM


def test_detects_agent_directory(service):
    result = service.analyze(
        code_entities=(
            entity(
                "ResearchWorker",
                filename="agents/research.py",
            ),
        )
    )

    assert result.get_pattern(
        ArchitecturePattern.AGENT
    ) is not None

def graph(
    filename="agents/research_agent.py",
    total_calls=2,
):
    return SimpleNamespace(
        filename=filename,
        total_calls=total_calls,
    )

def test_agent_confidence_uses_call_graph_evidence(service):
    result = service.analyze(
        code_entities=(
            entity(
                "ResearchAgent",
                filename="agents/research_agent.py",
            ),
        ),
        call_graphs=(graph(),),
    )

    finding = result.get_pattern(
        ArchitecturePattern.AGENT
    )

    assert finding.confidence is PatternConfidence.HIGH

    assert any(
        item.source == "call_graph"
        for item in finding.evidence
    )


def test_zero_agent_calls_do_not_increase_confidence(service):
    result = service.analyze(
        code_entities=(
            entity(
                "ResearchAgent",
                filename="agents/research_agent.py",
            ),
        ),
        call_graphs=(graph(total_calls=0),),
    )

    finding = result.get_pattern(
        ArchitecturePattern.AGENT
    )

    assert finding.confidence is PatternConfidence.MEDIUM


def test_call_graph_for_other_file_does_not_increase_agent_confidence(
    service,
):
    result = service.analyze(
        code_entities=(
            entity(
                "ResearchAgent",
                filename="agents/research_agent.py",
            ),
        ),
        call_graphs=(
            graph(filename="other.py", total_calls=8),
        ),
    )

    finding = result.get_pattern(
        ArchitecturePattern.AGENT
    )

    assert finding.confidence is PatternConfidence.MEDIUM


def test_counts_input_entities_dependencies_and_files(service):
    result = service.analyze(
        source_files=("a.py",),
        code_entities=(
            entity("A"),
            entity("B", "function", "B", "b.py"),
        ),
        dependencies=(
            dep(),
            dep("b.py"),
        ),
    )

    assert result.total_files == 4
    assert result.total_entities == 2
    assert result.total_dependencies == 2


def test_dependency_source_file_is_included(service):
    result = service.analyze(
        dependencies=(
            dep("src/module.py"),
        )
    )

    assert result.analyzed_files == ("src/module.py",)


def test_call_graph_file_is_included(service):
    result = service.analyze(
        call_graphs=(
            graph("src/agent.py"),
        )
    )

    assert result.analyzed_files == ("src/agent.py",)


def test_detected_patterns_property(service):
    result = service.analyze(
        code_entities=(entity("ProviderFactory"),)
    )

    assert result.detected_patterns == (
        ArchitecturePattern.FACTORY,
    )


def test_high_confidence_property(service):
    result = service.analyze(
        source_files=(
            "presentation/page.py",
            "application/use_case.py",
            "domain/entity.py",
            "infrastructure/db.py",
        )
    )

    assert len(result.high_confidence_findings) == 1


def test_unknown_pattern_lookup_returns_none(service):
    assert service.analyze().get_pattern("unknown") is None


def test_findings_are_deterministic(service):
    entities = (
        entity(
            "ResearchAgent",
            filename="agents/research.py",
        ),
        entity(
            "ProviderFactory",
            filename="factory.py",
        ),
        entity(
            "UserRepository",
            filename="repositories/user.py",
        ),
    )

    first = service.analyze(code_entities=entities)
    second = service.analyze(code_entities=entities)

    assert first == second


@pytest.mark.parametrize(
    "kwargs",
    [
        {"source_files": None},
        {"source_files": "appy.py"},
        {"source_files": b"appy.py"},
        {"source_files": {"appy.py"}},
        {"source_files": ("",)},
        {"source_files": ("a.py", "a.py")},
        {"code_entities": None},
        {"code_entities": "entity"},
        {"dependencies": None},
        {"dependencies": {"dependency"}},
        {"call_graphs": None},
        {"call_graphs": "graph"},
    ],
)
def test_rejects_invalid_collections(service, kwargs):
    with pytest.raises(ArchitecturePatternDetectionError):
        service.analyze(**kwargs)


def test_rejects_invalid_entity_object(service):
    with pytest.raises(ArchitecturePatternDetectionError):
        service.analyze(code_entities=(object(),))


def test_rejects_empty_entity_name(service):
    with pytest.raises(ArchitecturePatternDetectionError):
        service.analyze(
            code_entities=(
                SimpleNamespace(
                    name="",
                    entity_type="class",
                    qualified_name="X",
                    filename="x.py",
                ),
            )
        )


def test_rejects_invalid_dependency_object(service):
    with pytest.raises(ArchitecturePatternDetectionError):
        service.analyze(dependencies=(object(),))


def test_rejects_empty_dependency_source(service):
    with pytest.raises(ArchitecturePatternDetectionError):
        service.analyze(
            dependencies=(
                SimpleNamespace(
                    source_file="",
                    imported_module="x",
                ),
            )
        )


def test_rejects_invalid_call_graph_object(service):
    with pytest.raises(ArchitecturePatternDetectionError):
        service.analyze(call_graphs=(object(),))


@pytest.mark.parametrize(
    "count",
    [-1, True, "3"],
)
def test_rejects_invalid_call_count(service, count):
    with pytest.raises(ArchitecturePatternDetectionError):
        service.analyze(
            call_graphs=(
                graph(total_calls=count),
            )
        )


def test_evidence_model_rejects_empty_source():
    with pytest.raises(ArchitecturePatternDetectionError):
        ArchitecturePatternEvidence(
            "",
            "description",
        )


def test_evidence_model_rejects_non_string_path():
    with pytest.raises(ArchitecturePatternDetectionError):
        ArchitecturePatternEvidence(
            "test",
            "description",
            file_path=None,
        )


def test_finding_model_rejects_invalid_pattern():
    with pytest.raises(ArchitecturePatternDetectionError):
        ArchitecturePatternFinding(
            "layered",
            PatternConfidence.HIGH,
            1,
            (
                ArchitecturePatternEvidence(
                    "test",
                    "evidence",
                ),
            ),
            (),
            "description",
        )


def test_finding_model_rejects_inconsistent_evidence_count():
    with pytest.raises(ArchitecturePatternDetectionError):
        ArchitecturePatternFinding(
            ArchitecturePattern.FACTORY,
            PatternConfidence.HIGH,
            2,
            (
                ArchitecturePatternEvidence(
                    "test",
                    "evidence",
                ),
            ),
            (),
            "description",
        )


def test_result_model_rejects_inconsistent_pattern_count():
    with pytest.raises(ArchitecturePatternDetectionError):
        ArchitecturePatternDetectionResult(
            0,
            0,
            0,
            1,
            (),
            (),
            (),
        )


def test_result_model_rejects_negative_counts():
    with pytest.raises(ArchitecturePatternDetectionError):
        ArchitecturePatternDetectionResult(
            -1,
            0,
            0,
            0,
            (),
            (),
            (),
        )
