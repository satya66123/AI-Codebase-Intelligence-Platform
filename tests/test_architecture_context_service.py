
import pytest
from pathlib import Path

from appy.application.repository_input import RepositoryInfo
from appy.application.call_graph_service import (
    CallGraphResult,
    CallRecord,
)
from appy.application.inheritance_analyzer import (
    InheritanceAnalysisResult,
    InheritanceRecord,
)
from appy.application.architecture_context_service import (
    ArchitectureContextError,
    ArchitectureContextResult,
    ArchitectureContextService,
)


@pytest.fixture
def repository_info(tmp_path):
    return RepositoryInfo(
        root=tmp_path,
        name="sample-repository",
        is_git_repository=True,
    )


@pytest.fixture
def call_graph_results():
    first_calls = (
        CallRecord(
            filename="appy/service.py",
            caller="Service.process",
            caller_type="method",
            callee="validate",
            call_type="function",
            line=10,
        ),
        CallRecord(
            filename="appy/service.py",
            caller="Service.process",
            caller_type="method",
            callee="database.connect",
            call_type="attribute",
            line=15,
        ),
    )

    second_calls = (
        CallRecord(
            filename="appy/auth.py",
            caller="authenticate",
            caller_type="function",
            callee="verify_password",
            call_type="function",
            line=20,
        ),
    )

    return (
        CallGraphResult(
            filename="appy/service.py",
            calls=first_calls,
            total_calls=2,
        ),
        CallGraphResult(
            filename="appy/auth.py",
            calls=second_calls,
            total_calls=1,
        ),
    )


@pytest.fixture
def inheritance_results():
    first_relationships = (
        InheritanceRecord(
            filename="appy/service.py",
            class_name="UserService",
            qualified_class_name="service.UserService",
            base_class="BaseService",
            line=5,
            inheritance_type="single",
        ),
    )

    second_relationships = (
        InheritanceRecord(
            filename="appy/auth.py",
            class_name="AdminUser",
            qualified_class_name="auth.AdminUser",
            base_class="User",
            line=12,
            inheritance_type="single",
        ),
        InheritanceRecord(
            filename="appy/auth.py",
            class_name="AdminUser",
            qualified_class_name="auth.AdminUser",
            base_class="Auditable",
            line=12,
            inheritance_type="multiple",
        ),
    )

    return (
        InheritanceAnalysisResult(
            filename="appy/service.py",
            relationships=first_relationships,
            classes_without_bases=("service.Helper",),
            total_relationships=1,
        ),
        InheritanceAnalysisResult(
            filename="appy/auth.py",
            relationships=second_relationships,
            classes_without_bases=("auth.Token",),
            total_relationships=2,
        ),
    )


@pytest.fixture
def directory_tree():
    return (
        "sample-repository\n"
        "├── appy\n"
        "│   ├── auth.py\n"
        "│   └── service.py\n"
        "└── tests"
    )


@pytest.fixture
def service():
    return ArchitectureContextService()


# ---------------------------------------------------------
# Initialization tests
# ---------------------------------------------------------


def test_service_initialization():
    service = ArchitectureContextService()

    assert service is not None


# ---------------------------------------------------------
# Result model tests
# ---------------------------------------------------------


def test_result_creation(
    repository_info,
    directory_tree,
):
    result = ArchitectureContextResult(
        repository_name=repository_info.name,
        repository_root=str(repository_info.root),
        is_git_repository=True,
        directory_tree=directory_tree,
        call_graphs=(),
        inheritance_analyses=(),
        total_calls=0,
        total_inheritance_relationships=0,
        classes_without_bases=(),
    )

    assert result.repository_name == "sample-repository"
    assert result.total_calls == 0
    assert result.total_inheritance_relationships == 0


def test_result_rejects_empty_repository_name(directory_tree):
    with pytest.raises(ArchitectureContextError):
        ArchitectureContextResult(
            repository_name="",
            repository_root="/repository",
            is_git_repository=True,
            directory_tree=directory_tree,
            call_graphs=(),
            inheritance_analyses=(),
            total_calls=0,
            total_inheritance_relationships=0,
            classes_without_bases=(),
        )


def test_result_rejects_empty_repository_root(directory_tree):
    with pytest.raises(ArchitectureContextError):
        ArchitectureContextResult(
            repository_name="sample",
            repository_root="",
            is_git_repository=True,
            directory_tree=directory_tree,
            call_graphs=(),
            inheritance_analyses=(),
            total_calls=0,
            total_inheritance_relationships=0,
            classes_without_bases=(),
        )


def test_result_rejects_invalid_git_status(directory_tree):
    with pytest.raises(ArchitectureContextError):
        ArchitectureContextResult(
            repository_name="sample",
            repository_root="/repository",
            is_git_repository="yes",
            directory_tree=directory_tree,
            call_graphs=(),
            inheritance_analyses=(),
            total_calls=0,
            total_inheritance_relationships=0,
            classes_without_bases=(),
        )


def test_result_rejects_empty_directory_tree():
    with pytest.raises(ArchitectureContextError):
        ArchitectureContextResult(
            repository_name="sample",
            repository_root="/repository",
            is_git_repository=True,
            directory_tree="",
            call_graphs=(),
            inheritance_analyses=(),
            total_calls=0,
            total_inheritance_relationships=0,
            classes_without_bases=(),
        )


def test_result_rejects_non_tuple_call_graphs(directory_tree):
    with pytest.raises(ArchitectureContextError):
        ArchitectureContextResult(
            repository_name="sample",
            repository_root="/repository",
            is_git_repository=True,
            directory_tree=directory_tree,
            call_graphs=[],
            inheritance_analyses=(),
            total_calls=0,
            total_inheritance_relationships=0,
            classes_without_bases=(),
        )


def test_result_rejects_invalid_call_graph(directory_tree):
    with pytest.raises(ArchitectureContextError):
        ArchitectureContextResult(
            repository_name="sample",
            repository_root="/repository",
            is_git_repository=True,
            directory_tree=directory_tree,
            call_graphs=("invalid",),
            inheritance_analyses=(),
            total_calls=0,
            total_inheritance_relationships=0,
            classes_without_bases=(),
        )


def test_result_rejects_non_tuple_inheritance_analyses(
    directory_tree,
):
    with pytest.raises(ArchitectureContextError):
        ArchitectureContextResult(
            repository_name="sample",
            repository_root="/repository",
            is_git_repository=True,
            directory_tree=directory_tree,
            call_graphs=(),
            inheritance_analyses=[],
            total_calls=0,
            total_inheritance_relationships=0,
            classes_without_bases=(),
        )


def test_result_rejects_invalid_inheritance_analysis(
    directory_tree,
):
    with pytest.raises(ArchitectureContextError):
        ArchitectureContextResult(
            repository_name="sample",
            repository_root="/repository",
            is_git_repository=True,
            directory_tree=directory_tree,
            call_graphs=(),
            inheritance_analyses=("invalid",),
            total_calls=0,
            total_inheritance_relationships=0,
            classes_without_bases=(),
        )


def test_result_rejects_negative_total_calls(directory_tree):
    with pytest.raises(ArchitectureContextError):
        ArchitectureContextResult(
            repository_name="sample",
            repository_root="/repository",
            is_git_repository=True,
            directory_tree=directory_tree,
            call_graphs=(),
            inheritance_analyses=(),
            total_calls=-1,
            total_inheritance_relationships=0,
            classes_without_bases=(),
        )


def test_result_rejects_boolean_total_calls(directory_tree):
    with pytest.raises(ArchitectureContextError):
        ArchitectureContextResult(
            repository_name="sample",
            repository_root="/repository",
            is_git_repository=True,
            directory_tree=directory_tree,
            call_graphs=(),
            inheritance_analyses=(),
            total_calls=True,
            total_inheritance_relationships=0,
            classes_without_bases=(),
        )


def test_result_rejects_negative_inheritance_total(directory_tree):
    with pytest.raises(ArchitectureContextError):
        ArchitectureContextResult(
            repository_name="sample",
            repository_root="/repository",
            is_git_repository=True,
            directory_tree=directory_tree,
            call_graphs=(),
            inheritance_analyses=(),
            total_calls=0,
            total_inheritance_relationships=-1,
            classes_without_bases=(),
        )


def test_result_rejects_call_total_mismatch(
    directory_tree,
    call_graph_results,
):
    with pytest.raises(ArchitectureContextError):
        ArchitectureContextResult(
            repository_name="sample",
            repository_root="/repository",
            is_git_repository=True,
            directory_tree=directory_tree,
            call_graphs=call_graph_results,
            inheritance_analyses=(),
            total_calls=1,
            total_inheritance_relationships=0,
            classes_without_bases=(),
        )


def test_result_rejects_inheritance_total_mismatch(
    directory_tree,
    inheritance_results,
):
    with pytest.raises(ArchitectureContextError):
        ArchitectureContextResult(
            repository_name="sample",
            repository_root="/repository",
            is_git_repository=True,
            directory_tree=directory_tree,
            call_graphs=(),
            inheritance_analyses=inheritance_results,
            total_calls=0,
            total_inheritance_relationships=1,
            classes_without_bases=(),
        )


def test_result_rejects_non_tuple_classes_without_bases(
    directory_tree,
):
    with pytest.raises(ArchitectureContextError):
        ArchitectureContextResult(
            repository_name="sample",
            repository_root="/repository",
            is_git_repository=True,
            directory_tree=directory_tree,
            call_graphs=(),
            inheritance_analyses=(),
            total_calls=0,
            total_inheritance_relationships=0,
            classes_without_bases=[],
        )


def test_result_rejects_empty_class_name(directory_tree):
    with pytest.raises(ArchitectureContextError):
        ArchitectureContextResult(
            repository_name="sample",
            repository_root="/repository",
            is_git_repository=True,
            directory_tree=directory_tree,
            call_graphs=(),
            inheritance_analyses=(),
            total_calls=0,
            total_inheritance_relationships=0,
            classes_without_bases=("",),
        )


# ---------------------------------------------------------
# Context construction tests
# ---------------------------------------------------------


def test_build_context_returns_result(
    service,
    repository_info,
    directory_tree,
):
    result = service.build_context(
        repository_info=repository_info,
        directory_tree=directory_tree,
    )

    assert isinstance(result, ArchitectureContextResult)


def test_build_context_preserves_repository_name(
    service,
    repository_info,
    directory_tree,
):
    result = service.build_context(
        repository_info,
        directory_tree,
    )

    assert result.repository_name == repository_info.name


def test_build_context_preserves_repository_root(
    service,
    repository_info,
    directory_tree,
):
    result = service.build_context(
        repository_info,
        directory_tree,
    )

    assert result.repository_root == str(repository_info.root)


def test_build_context_preserves_git_status(
    service,
    repository_info,
    directory_tree,
):
    result = service.build_context(
        repository_info,
        directory_tree,
    )

    assert result.is_git_repository is True


def test_build_context_preserves_directory_tree(
    service,
    repository_info,
    directory_tree,
):
    result = service.build_context(
        repository_info,
        directory_tree,
    )

    assert result.directory_tree == directory_tree


def test_build_context_includes_call_graphs(
    service,
    repository_info,
    directory_tree,
    call_graph_results,
):
    result = service.build_context(
        repository_info,
        directory_tree,
        call_graph_results=call_graph_results,
    )

    assert result.call_graphs == call_graph_results


def test_build_context_includes_inheritance_analyses(
    service,
    repository_info,
    directory_tree,
    inheritance_results,
):
    result = service.build_context(
        repository_info,
        directory_tree,
        inheritance_results=inheritance_results,
    )

    assert result.inheritance_analyses == inheritance_results


def test_build_context_calculates_total_calls(
    service,
    repository_info,
    directory_tree,
    call_graph_results,
):
    result = service.build_context(
        repository_info,
        directory_tree,
        call_graph_results=call_graph_results,
    )

    assert result.total_calls == 3


def test_build_context_calculates_total_inheritance_relationships(
    service,
    repository_info,
    directory_tree,
    inheritance_results,
):
    result = service.build_context(
        repository_info,
        directory_tree,
        inheritance_results=inheritance_results,
    )

    assert result.total_inheritance_relationships == 3


def test_build_context_collects_classes_without_bases(
    service,
    repository_info,
    directory_tree,
    inheritance_results,
):
    result = service.build_context(
        repository_info,
        directory_tree,
        inheritance_results=inheritance_results,
    )

    assert result.classes_without_bases == (
        "service.Helper",
        "auth.Token",
    )


def test_build_context_combines_all_architecture_information(
    service,
    repository_info,
    directory_tree,
    call_graph_results,
    inheritance_results,
):
    result = service.build_context(
        repository_info=repository_info,
        directory_tree=directory_tree,
        call_graph_results=call_graph_results,
        inheritance_results=inheritance_results,
    )

    assert result.total_calls == 3
    assert result.total_inheritance_relationships == 3
    assert len(result.call_graphs) == 2
    assert len(result.inheritance_analyses) == 2


# ---------------------------------------------------------
# Relevant file filtering tests
# ---------------------------------------------------------


def test_build_context_filters_call_graphs(
    service,
    repository_info,
    directory_tree,
    call_graph_results,
):
    result = service.build_context(
        repository_info,
        directory_tree,
        call_graph_results=call_graph_results,
        relevant_files=("appy/service.py",),
    )

    assert len(result.call_graphs) == 1
    assert result.call_graphs[0].filename == "appy/service.py"
    assert result.total_calls == 2


def test_build_context_filters_inheritance_analyses(
    service,
    repository_info,
    directory_tree,
    inheritance_results,
):
    result = service.build_context(
        repository_info,
        directory_tree,
        inheritance_results=inheritance_results,
        relevant_files=("appy/auth.py",),
    )

    assert len(result.inheritance_analyses) == 1
    assert result.inheritance_analyses[0].filename == "appy/auth.py"
    assert result.total_inheritance_relationships == 2


def test_build_context_filters_both_analysis_types(
    service,
    repository_info,
    directory_tree,
    call_graph_results,
    inheritance_results,
):
    result = service.build_context(
        repository_info,
        directory_tree,
        call_graph_results=call_graph_results,
        inheritance_results=inheritance_results,
        relevant_files=("appy/service.py",),
    )

    assert len(result.call_graphs) == 1
    assert len(result.inheritance_analyses) == 1
    assert result.total_calls == 2
    assert result.total_inheritance_relationships == 1


def test_build_context_returns_empty_analysis_for_unmatched_files(
    service,
    repository_info,
    directory_tree,
    call_graph_results,
    inheritance_results,
):
    result = service.build_context(
        repository_info,
        directory_tree,
        call_graph_results=call_graph_results,
        inheritance_results=inheritance_results,
        relevant_files=("appy/missing.py",),
    )

    assert result.call_graphs == ()
    assert result.inheritance_analyses == ()
    assert result.total_calls == 0
    assert result.total_inheritance_relationships == 0
    assert result.classes_without_bases == ()


# ---------------------------------------------------------
# Empty input tests
# ---------------------------------------------------------


def test_build_context_accepts_empty_call_graphs(
    service,
    repository_info,
    directory_tree,
):
    result = service.build_context(
        repository_info,
        directory_tree,
        call_graph_results=(),
    )

    assert result.call_graphs == ()
    assert result.total_calls == 0


def test_build_context_accepts_empty_inheritance_results(
    service,
    repository_info,
    directory_tree,
):
    result = service.build_context(
        repository_info,
        directory_tree,
        inheritance_results=(),
    )

    assert result.inheritance_analyses == ()
    assert result.total_inheritance_relationships == 0


def test_build_context_accepts_empty_relevant_files(
    service,
    repository_info,
    directory_tree,
    call_graph_results,
    inheritance_results,
):
    result = service.build_context(
        repository_info,
        directory_tree,
        call_graph_results=call_graph_results,
        inheritance_results=inheritance_results,
        relevant_files=(),
    )

    assert result.call_graphs == ()
    assert result.inheritance_analyses == ()


# ---------------------------------------------------------
# Invalid input tests
# ---------------------------------------------------------


def test_build_context_rejects_invalid_repository_info(
    service,
    directory_tree,
):
    with pytest.raises(ArchitectureContextError):
        service.build_context(
            repository_info="invalid",
            directory_tree=directory_tree,
        )


def test_build_context_rejects_none_repository_info(
    service,
    directory_tree,
):
    with pytest.raises(ArchitectureContextError):
        service.build_context(
            repository_info=None,
            directory_tree=directory_tree,
        )


def test_build_context_rejects_empty_directory_tree(
    service,
    repository_info,
):
    with pytest.raises(ArchitectureContextError):
        service.build_context(
            repository_info,
            "",
        )


def test_build_context_rejects_invalid_call_graph_results(
    service,
    repository_info,
    directory_tree,
):
    with pytest.raises(ArchitectureContextError):
        service.build_context(
            repository_info,
            directory_tree,
            call_graph_results=("invalid",),
        )


def test_build_context_rejects_none_call_graph_results(
    service,
    repository_info,
    directory_tree,
):
    with pytest.raises(ArchitectureContextError):
        service.build_context(
            repository_info,
            directory_tree,
            call_graph_results=None,
        )


def test_build_context_rejects_invalid_inheritance_results(
    service,
    repository_info,
    directory_tree,
):
    with pytest.raises(ArchitectureContextError):
        service.build_context(
            repository_info,
            directory_tree,
            inheritance_results=("invalid",),
        )


def test_build_context_rejects_none_inheritance_results(
    service,
    repository_info,
    directory_tree,
):
    with pytest.raises(ArchitectureContextError):
        service.build_context(
            repository_info,
            directory_tree,
            inheritance_results=None,
        )


def test_build_context_rejects_string_relevant_files(
    service,
    repository_info,
    directory_tree,
):
    with pytest.raises(ArchitectureContextError):
        service.build_context(
            repository_info,
            directory_tree,
            relevant_files="appy/service.py",
        )


def test_build_context_rejects_invalid_relevant_filename(
    service,
    repository_info,
    directory_tree,
):
    with pytest.raises(ArchitectureContextError):
        service.build_context(
            repository_info,
            directory_tree,
            relevant_files=("appy/service.py", ""),
        )
