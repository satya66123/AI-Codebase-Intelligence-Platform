
from types import SimpleNamespace

import pytest

from appy.application.module_responsibility_analysis_service import (
    ModuleResponsibility,
    ModuleResponsibilityAnalysisError,
    ModuleResponsibilityAnalysisResult,
    ModuleResponsibilityAnalysisService,
    ModuleResponsibilityEvidence,
    ModuleResponsibilityFinding,
    ResponsibilityConfidence,
)


@pytest.fixture
def service():
    return ModuleResponsibilityAnalysisService()


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


def dependency(source_file="appy/module.py"):
    return SimpleNamespace(source_file=source_file)


def call_graph(filename="appy/module.py", total_calls=3):
    return SimpleNamespace(
        filename=filename,
        total_calls=total_calls,
    )


def test_empty_repository(service):
    result = service.analyze()

    assert result.total_modules == 0
    assert result.classified_modules == 0
    assert result.unclassified_modules == 0
    assert result.findings == ()


def test_classifies_api_directory(service):
    result = service.analyze(
        source_files=("appy/api/users.py",)
    )

    finding = result.get_module("appy/api/users.py")

    assert finding.responsibility is ModuleResponsibility.API
    assert finding.confidence is ResponsibilityConfidence.HIGH


def test_classifies_presentation_directory(service):
    result = service.analyze(
        source_files=("appy/views/dashboard.py",)
    )

    assert result.get_module(
        "appy/views/dashboard.py"
    ).responsibility is ModuleResponsibility.PRESENTATION


def test_classifies_application_directory(service):
    result = service.analyze(
        source_files=("appy/application/workflow.py",)
    )

    assert result.get_module(
        "appy/application/workflow.py"
    ).responsibility is ModuleResponsibility.APPLICATION


def test_classifies_domain_directory(service):
    result = service.analyze(
        source_files=("appy/domain/customer.py",)
    )

    assert result.get_module(
        "appy/domain/customer.py"
    ).responsibility is ModuleResponsibility.DOMAIN


def test_classifies_infrastructure_directory(service):
    result = service.analyze(
        source_files=("appy/infrastructure/email.py",)
    )

    assert result.get_module(
        "appy/infrastructure/email.py"
    ).responsibility is ModuleResponsibility.INFRASTRUCTURE


def test_classifies_data_access_directory(service):
    result = service.analyze(
        source_files=("appy/repositories/customer.py",)
    )

    assert result.get_module(
        "appy/repositories/customer.py"
    ).responsibility is ModuleResponsibility.DATA_ACCESS


def test_classifies_configuration_directory(service):
    result = service.analyze(
        source_files=("appy/config/settings.py",)
    )

    assert result.get_module(
        "appy/config/settings.py"
    ).responsibility is ModuleResponsibility.CONFIGURATION


def test_classifies_testing_directory(service):
    result = service.analyze(
        source_files=("tests/test_service.py",)
    )

    assert result.get_module(
        "tests/test_service.py"
    ).responsibility is ModuleResponsibility.TESTING


def test_classifies_utilities_directory(service):
    result = service.analyze(
        source_files=("appy/utils/helpers.py",)
    )

    assert result.get_module(
        "appy/utils/helpers.py"
    ).responsibility is ModuleResponsibility.UTILITIES


def test_classifies_agent_directory(service):
    result = service.analyze(
        source_files=("appy/agents/research.py",)
    )

    assert result.get_module(
        "appy/agents/research.py"
    ).responsibility is ModuleResponsibility.AGENT


def test_classifies_service_directory(service):
    result = service.analyze(
        source_files=("appy/services/payment.py",)
    )

    assert result.get_module(
        "appy/services/payment.py"
    ).responsibility is ModuleResponsibility.SERVICE


def test_directory_classification_takes_precedence(service):
    result = service.analyze(
        source_files=("appy/services/user_repository.py",)
    )

    assert result.get_module(
        "appy/services/user_repository.py"
    ).responsibility is ModuleResponsibility.SERVICE


def test_classifies_router_filename(service):
    result = service.analyze(
        source_files=("appy/user_router.py",)
    )

    assert result.get_module(
        "appy/user_router.py"
    ).responsibility is ModuleResponsibility.API


def test_classifies_view_filename(service):
    result = service.analyze(
        source_files=("appy/dashboard_view.py",)
    )

    assert result.get_module(
        "appy/dashboard_view.py"
    ).responsibility is ModuleResponsibility.PRESENTATION


def test_classifies_use_case_filename(service):
    result = service.analyze(
        source_files=("appy/create_user_use_case.py",)
    )

    assert result.get_module(
        "appy/create_user_use_case.py"
    ).responsibility is ModuleResponsibility.APPLICATION


def test_classifies_entity_filename(service):
    result = service.analyze(
        source_files=("appy/customer_entity.py",)
    )

    assert result.get_module(
        "appy/customer_entity.py"
    ).responsibility is ModuleResponsibility.DOMAIN


def test_classifies_adapter_filename(service):
    result = service.analyze(
        source_files=("appy/payment_adapter.py",)
    )

    assert result.get_module(
        "appy/payment_adapter.py"
    ).responsibility is ModuleResponsibility.INFRASTRUCTURE


def test_classifies_repository_filename(service):
    result = service.analyze(
        source_files=("appy/customer_repository.py",)
    )

    assert result.get_module(
        "appy/customer_repository.py"
    ).responsibility is ModuleResponsibility.DATA_ACCESS


def test_classifies_settings_filename(service):
    result = service.analyze(
        source_files=("appy/application_settings.py",)
    )

    assert result.get_module(
        "appy/application_settings.py"
    ).responsibility is ModuleResponsibility.CONFIGURATION


def test_classifies_test_filename(service):
    result = service.analyze(
        source_files=("appy/test_customer.py",)
    )

    assert result.get_module(
        "appy/test_customer.py"
    ).responsibility is ModuleResponsibility.TESTING


def test_classifies_helpers_filename(service):
    result = service.analyze(
        source_files=("appy/string_helpers.py",)
    )

    assert result.get_module(
        "appy/string_helpers.py"
    ).responsibility is ModuleResponsibility.UTILITIES


def test_classifies_agent_filename(service):
    result = service.analyze(
        source_files=("appy/research_agent.py",)
    )

    assert result.get_module(
        "appy/research_agent.py"
    ).responsibility is ModuleResponsibility.AGENT


def test_classifies_service_filename(service):
    result = service.analyze(
        source_files=("appy/payment_service.py",)
    )

    assert result.get_module(
        "appy/payment_service.py"
    ).responsibility is ModuleResponsibility.SERVICE


def test_classifies_using_entity_names(service):
    result = service.analyze(
        source_files=("appy/operations.py",),
        code_entities=(
            entity(
                "CustomerRepository",
                filename="appy/operations.py",
            ),
        ),
    )

    finding = result.get_module("appy/operations.py")

    assert finding.responsibility is ModuleResponsibility.DATA_ACCESS
    assert finding.confidence is ResponsibilityConfidence.MEDIUM


def test_multiple_matching_entities_increase_confidence(service):
    result = service.analyze(
        source_files=("appy/operations.py",),
        code_entities=(
            entity(
                "CustomerRepository",
                filename="appy/operations.py",
            ),
            entity(
                "OrderRepository",
                filename="appy/operations.py",
            ),
        ),
    )

    finding = result.get_module("appy/operations.py")

    assert finding.confidence is ResponsibilityConfidence.HIGH
    assert finding.entity_count == 2


def test_unrecognized_module_is_unclassified(service):
    result = service.analyze(
        source_files=("appy/processor.py",)
    )

    assert result.unclassified_files == ("appy/processor.py",)
    assert result.has_unclassified_modules


def test_dependencies_contribute_to_module_inventory(service):
    result = service.analyze(
        dependencies=(
            dependency("appy/services/user.py"),
        )
    )

    assert result.total_modules == 1
    assert result.classified_modules == 1


def test_call_graphs_contribute_to_module_inventory(service):
    result = service.analyze(
        call_graphs=(
            call_graph("appy/agents/research.py", 5),
        )
    )

    assert result.total_modules == 1
    assert result.total_calls == 5


def test_counts_entities_dependencies_and_calls(service):
    result = service.analyze(
        source_files=("appy/services/user.py",),
        code_entities=(
            entity("UserService"),
            entity(
                "UserHelper",
                "function",
                "UserHelper",
                "appy/services/user.py",
            ),
        ),
        dependencies=(
            dependency(),
            dependency(),
        ),
        call_graphs=(
            call_graph(total_calls=4),
            call_graph(total_calls=3),
        ),
    )

    assert result.total_entities == 2
    assert result.total_dependencies == 2
    assert result.total_calls == 7


def test_module_findings_are_sorted(service):
    result = service.analyze(
        source_files=(
            "appy/services/z.py",
            "appy/api/a.py",
        )
    )

    assert tuple(
        item.file_path for item in result.findings
    ) == (
        "appy/api/a.py",
        "appy/services/z.py",
    )


def test_normalizes_windows_paths(service):
    result = service.analyze(
        source_files=(r"appy\services\user.py",)
    )

    assert result.get_module(
        "appy/services/user.py"
    ) is not None


def test_get_by_responsibility(service):
    result = service.analyze(
        source_files=(
            "appy/services/user.py",
            "appy/services/order.py",
            "appy/api/routes.py",
        )
    )

    findings = result.get_by_responsibility(
        ModuleResponsibility.SERVICE
    )

    assert len(findings) == 2


def test_get_by_responsibility_accepts_string(service):
    result = service.analyze(
        source_files=("appy/api/routes.py",)
    )

    findings = result.get_by_responsibility("api")

    assert len(findings) == 1


def test_unknown_responsibility_lookup_returns_empty(service):
    result = service.analyze(
        source_files=("appy/api/routes.py",)
    )

    assert result.get_by_responsibility("unknown-value") == ()


def test_responsibilities_property(service):
    result = service.analyze(
        source_files=(
            "appy/api/routes.py",
            "appy/services/user.py",
        )
    )

    assert set(result.responsibilities) == {
        ModuleResponsibility.API,
        ModuleResponsibility.SERVICE,
    }


def test_high_confidence_findings_property(service):
    result = service.analyze(
        source_files=("appy/services/user.py",)
    )

    assert len(result.high_confidence_findings) == 1


def test_result_reports_incomplete_classification(service):
    result = service.analyze(
        source_files=(
            "appy/api/routes.py",
            "appy/processor.py",
        )
    )

    assert not result.is_complete
    assert not result.healthy


def test_result_reports_complete_classification(service):
    result = service.analyze(
        source_files=("appy/api/routes.py",)
    )

    assert result.is_complete
    assert result.healthy


def test_analysis_is_deterministic(service):
    files = (
        "appy/services/user.py",
        "appy/api/routes.py",
        "appy/domain/customer.py",
    )

    assert service.analyze(source_files=files) == service.analyze(
        source_files=files
    )


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
        {"code_entities": {"entity"}},
        {"dependencies": None},
        {"dependencies": "dependency"},
        {"dependencies": {"dependency"}},
        {"call_graphs": None},
        {"call_graphs": "graph"},
        {"call_graphs": {"graph"}},
    ],
)
def test_rejects_invalid_collections(service, kwargs):
    with pytest.raises(ModuleResponsibilityAnalysisError):
        service.analyze(**kwargs)


def test_rejects_invalid_entity_object(service):
    with pytest.raises(ModuleResponsibilityAnalysisError):
        service.analyze(code_entities=(object(),))


def test_rejects_empty_entity_name(service):
    with pytest.raises(ModuleResponsibilityAnalysisError):
        service.analyze(
            code_entities=(
                SimpleNamespace(
                    name="",
                    entity_type="class",
                    qualified_name="Customer",
                    filename="customer.py",
                ),
            )
        )


def test_rejects_invalid_dependency_object(service):
    with pytest.raises(ModuleResponsibilityAnalysisError):
        service.analyze(dependencies=(object(),))


def test_rejects_empty_dependency_source_file(service):
    with pytest.raises(ModuleResponsibilityAnalysisError):
        service.analyze(
            dependencies=(
                SimpleNamespace(source_file=""),
            )
        )


def test_rejects_invalid_call_graph_object(service):
    with pytest.raises(ModuleResponsibilityAnalysisError):
        service.analyze(call_graphs=(object(),))


@pytest.mark.parametrize("value", [-1, True, "3"])
def test_rejects_invalid_call_count(service, value):
    with pytest.raises(ModuleResponsibilityAnalysisError):
        service.analyze(
            call_graphs=(
                call_graph(total_calls=value),
            )
        )


def test_evidence_model_rejects_empty_source():
    with pytest.raises(ModuleResponsibilityAnalysisError):
        ModuleResponsibilityEvidence("", "description")


def test_evidence_model_rejects_empty_description():
    with pytest.raises(ModuleResponsibilityAnalysisError):
        ModuleResponsibilityEvidence("test", "")


def test_finding_model_rejects_invalid_responsibility():
    with pytest.raises(ModuleResponsibilityAnalysisError):
        ModuleResponsibilityFinding(
            "module",
            "module.py",
            "unknown",
            ResponsibilityConfidence.HIGH,
            1,
            (
                ModuleResponsibilityEvidence(
                    "test",
                    "evidence",
                ),
            ),
            0,
            0,
            0,
            "description",
        )


def test_finding_model_rejects_invalid_evidence_count():
    with pytest.raises(ModuleResponsibilityAnalysisError):
        ModuleResponsibilityFinding(
            "module",
            "module.py",
            ModuleResponsibility.API,
            ResponsibilityConfidence.HIGH,
            2,
            (
                ModuleResponsibilityEvidence(
                    "test",
                    "evidence",
                ),
            ),
            0,
            0,
            0,
            "description",
        )


def test_finding_model_rejects_negative_entity_count():
    with pytest.raises(ModuleResponsibilityAnalysisError):
        ModuleResponsibilityFinding(
            "module",
            "module.py",
            ModuleResponsibility.API,
            ResponsibilityConfidence.HIGH,
            1,
            (
                ModuleResponsibilityEvidence(
                    "test",
                    "evidence",
                ),
            ),
            -1,
            0,
            0,
            "description",
        )


def test_result_model_rejects_inconsistent_module_counts():
    with pytest.raises(ModuleResponsibilityAnalysisError):
        ModuleResponsibilityAnalysisResult(
            2,
            1,
            0,
            (),
            (),
            0,
            0,
            0,
        )


def test_result_model_rejects_negative_total():
    with pytest.raises(ModuleResponsibilityAnalysisError):
        ModuleResponsibilityAnalysisResult(
            -1,
            0,
            1,
            (),
            ("unknown.py",),
            0,
            0,
            0,
        )
