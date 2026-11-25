
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.application.reasoning_orchestration_service import (
    ReasoningOrchestrationError,
    ReasoningOrchestrationService,
)
from app.application.intent_detection_service import QueryIntent


@pytest.fixture
def dependencies(tmp_path):
    repository_info = SimpleNamespace(
        root=tmp_path,
        name="sample_repo",
        is_git_repository=True,
    )

    discovery_result = SimpleNamespace(
        repository=repository_info,
        repository_map="sample_repo/\n    main.py",
        metadata={"files": []},
    )

    question_analysis = SimpleNamespace(
        question="Explain the application architecture",
        intent=QueryIntent.ARCHITECTURE,
        confidence=0.95,
        matched_terms=("architecture",),
    )

    repository_result = SimpleNamespace(
        retrieval_data=SimpleNamespace(memories=()),
    )

    relevant_files = SimpleNamespace(
        files=(),
    )

    relevant_code = SimpleNamespace(
        code_entities=(),
    )

    dependency_context = SimpleNamespace()
    architecture_context = SimpleNamespace()

    combined_context = SimpleNamespace(
        source_files=(),
        entity_ids=(),
    )

    reasoning_service = SimpleNamespace(
        provider_name="openai",
        generate_answer=Mock(
            return_value="The application uses a layered architecture."
        ),
    )

    ai_service = object()

    mocks = {
        "repository_discovery_service": Mock(),
        "source_file_selection_service": Mock(),
        "language_parser_factory": Mock(),
        "code_entity_extractor": Mock(),
        "code_indexing_service": Mock(),
        "import_analyzer": Mock(),
        "call_graph_service": Mock(),
        "inheritance_analyzer": Mock(),
        "question_analysis_agent": Mock(),
        "repository_retrieval_service": Mock(),
        "relevant_file_retrieval_service": Mock(),
        "relevant_code_retrieval_service": Mock(),
        "dependency_context_service": Mock(),
        "architecture_context_service": Mock(),
        "context_builder": Mock(),
        "ai_service_factory": Mock(return_value=ai_service),
        "reasoning_service_factory": Mock(
            return_value=reasoning_service
        ),
    }

    mocks["repository_discovery_service"].discover.return_value = (
        discovery_result
    )

    mocks[
        "source_file_selection_service"
    ].select_source_files.return_value = SimpleNamespace(files=())

    mocks["question_analysis_agent"].analyze.return_value = (
        question_analysis
    )

    mocks["repository_retrieval_service"].retrieve.return_value = (
        repository_result
    )

    mocks["relevant_file_retrieval_service"].retrieve.return_value = (
        relevant_files
    )

    mocks["relevant_code_retrieval_service"].retrieve.return_value = (
        relevant_code
    )

    mocks["dependency_context_service"].retrieve.return_value = (
        dependency_context
    )

    mocks["architecture_context_service"].build_context.return_value = (
        architecture_context
    )

    mocks["context_builder"].build_context.return_value = combined_context

    return {
        "mocks": mocks,
        "repository_info": repository_info,
        "discovery_result": discovery_result,
        "question_analysis": question_analysis,
        "repository_result": repository_result,
        "relevant_files": relevant_files,
        "relevant_code": relevant_code,
        "combined_context": combined_context,
        "reasoning_service": reasoning_service,
        "ai_service": ai_service,
        "tmp_path": tmp_path,
    }


@pytest.fixture
def service(dependencies):
    mocks = dependencies["mocks"]

    return ReasoningOrchestrationService(
        repository_retrieval_service=mocks[
            "repository_retrieval_service"
        ],
        relevant_file_retrieval_service=mocks[
            "relevant_file_retrieval_service"
        ],
        relevant_code_retrieval_service=mocks[
            "relevant_code_retrieval_service"
        ],
        dependency_context_service=mocks[
            "dependency_context_service"
        ],
        architecture_context_service=mocks[
            "architecture_context_service"
        ],
        ai_service_factory=mocks["ai_service_factory"],
        repository_discovery_service=mocks[
            "repository_discovery_service"
        ],
        source_file_selection_service=mocks[
            "source_file_selection_service"
        ],
        language_parser_factory=mocks[
            "language_parser_factory"
        ],
        code_entity_extractor=mocks[
            "code_entity_extractor"
        ],
        code_indexing_service=mocks[
            "code_indexing_service"
        ],
        import_analyzer=mocks["import_analyzer"],
        call_graph_service=mocks["call_graph_service"],
        inheritance_analyzer=mocks["inheritance_analyzer"],
        question_analysis_agent=mocks[
            "question_analysis_agent"
        ],
        context_builder=mocks["context_builder"],
        reasoning_service_factory=mocks[
            "reasoning_service_factory"
        ],
    )


def run_answer(service, tmp_path, **overrides):
    arguments = {
        "repository_path": tmp_path,
        "repository_id": "sample-repository-id",
        "question": "Explain the application architecture",
        "provider_name": "openai",
        "model": "gpt-4o",
    }

    arguments.update(overrides)

    return service.answer_question(**arguments)


def test_constructor_requires_ai_service_factory(dependencies):
    mocks = dependencies["mocks"]

    with pytest.raises(
        ReasoningOrchestrationError,
        match="AI service factory must be callable",
    ):
        ReasoningOrchestrationService(
            repository_retrieval_service=mocks[
                "repository_retrieval_service"
            ],
            relevant_file_retrieval_service=mocks[
                "relevant_file_retrieval_service"
            ],
            relevant_code_retrieval_service=mocks[
                "relevant_code_retrieval_service"
            ],
            dependency_context_service=mocks[
                "dependency_context_service"
            ],
            architecture_context_service=mocks[
                "architecture_context_service"
            ],
            ai_service_factory=None,
        )


def test_successful_orchestration_returns_reasoning_response(
    service,
    dependencies,
):
    response = run_answer(
        service,
        dependencies["tmp_path"],
    )

    assert response.question == (
        "Explain the application architecture"
    )
    assert response.answer == (
        "The application uses a layered architecture."
    )
    assert response.intent == QueryIntent.ARCHITECTURE
    assert response.provider_name == "openai"
    assert response.model_name == "gpt-4o"
    assert response.evidence_sufficient is False


def test_question_analysis_runs_before_repository_discovery(
    service,
    dependencies,
):
    mocks = dependencies["mocks"]

    run_answer(service, dependencies["tmp_path"])

    assert mocks["question_analysis_agent"].analyze.called
    assert mocks["repository_discovery_service"].discover.called

    assert (
        mocks["question_analysis_agent"].analyze.call_args_list[0]
        .args[0]
        == "Explain the application architecture"
    )


def test_repository_discovery_receives_repository_path(
    service,
    dependencies,
):
    mocks = dependencies["mocks"]

    run_answer(service, dependencies["tmp_path"])

    mocks["repository_discovery_service"].discover.assert_called_once_with(
        repository_path=dependencies["tmp_path"],
        save_index=True,
    )


def test_source_selection_uses_discovered_file_metadata(
    service,
    dependencies,
):
    mocks = dependencies["mocks"]

    run_answer(service, dependencies["tmp_path"])

    mocks[
        "source_file_selection_service"
    ].select_source_files.assert_called_once_with([])


def test_code_indexing_runs_even_when_no_files_are_parseable(
    service,
    dependencies,
):
    mocks = dependencies["mocks"]

    run_answer(service, dependencies["tmp_path"])

    mocks["code_indexing_service"].build_index.assert_called_once_with([])


def test_repository_retrieval_receives_repository_id_and_analysis(
    service,
    dependencies,
):
    mocks = dependencies["mocks"]

    run_answer(service, dependencies["tmp_path"])

    mocks["repository_retrieval_service"].retrieve.assert_called_once_with(
        repository_id="sample-repository-id",
        analysis_result=dependencies["question_analysis"],
        limit=10,
    )


def test_relevant_file_retrieval_receives_code_index_and_analysis(
    service,
    dependencies,
):
    mocks = dependencies["mocks"]

    run_answer(service, dependencies["tmp_path"])

    mocks["relevant_file_retrieval_service"].retrieve.assert_called_once()

    call_kwargs = (
        mocks["relevant_file_retrieval_service"]
        .retrieve.call_args.kwargs
    )

    assert call_kwargs["analysis_result"] == (
        dependencies["question_analysis"]
    )
    assert call_kwargs["limit"] == 10


def test_context_builder_receives_all_context_sections(
    service,
    dependencies,
):
    mocks = dependencies["mocks"]

    run_answer(service, dependencies["tmp_path"])

    mocks["context_builder"].build_context.assert_called_once()

    call_kwargs = mocks["context_builder"].build_context.call_args.kwargs

    assert call_kwargs["question_analysis"] == (
        dependencies["question_analysis"]
    )
    assert call_kwargs["repository_result"] == (
        dependencies["repository_result"]
    )
    assert call_kwargs["relevant_files"] == (
        dependencies["relevant_files"]
    )
    assert call_kwargs["relevant_code"] == (
        dependencies["relevant_code"]
    )
    assert call_kwargs["max_characters"] == 12000


def test_ai_service_factory_receives_selected_provider(
    service,
    dependencies,
):
    run_answer(service, dependencies["tmp_path"])

    dependencies["mocks"]["ai_service_factory"].assert_called_once_with(
        "openai"
    )


def test_reasoning_service_factory_receives_ai_service(
    service,
    dependencies,
):
    run_answer(service, dependencies["tmp_path"])

    dependencies[
        "mocks"
    ]["reasoning_service_factory"].assert_called_once_with(
        ai_service=dependencies["ai_service"]
    )


def test_reasoning_service_receives_selected_model(
    service,
    dependencies,
):
    run_answer(
        service,
        dependencies["tmp_path"],
        model="gpt-4o-mini",
    )

    dependencies["reasoning_service"].generate_answer.assert_called_once()

    call_kwargs = (
        dependencies["reasoning_service"]
        .generate_answer.call_args.kwargs
    )

    assert call_kwargs["model"] == "gpt-4o-mini"


def test_retrieved_memories_mark_evidence_as_sufficient(
    service,
    dependencies,
):
    dependencies["repository_result"].retrieval_data.memories = (
        SimpleNamespace(memory_id="memory-1"),
    )

    response = run_answer(
        service,
        dependencies["tmp_path"],
    )

    assert response.evidence_sufficient is True


@pytest.mark.parametrize(
    "field,value",
    [
        ("repository_id", ""),
        ("question", ""),
        ("provider_name", ""),
        ("model", ""),
    ],
)
def test_empty_required_string_is_rejected(
    service,
    dependencies,
    field,
    value,
):
    with pytest.raises(ReasoningOrchestrationError):
        run_answer(
            service,
            dependencies["tmp_path"],
            **{field: value},
        )


@pytest.mark.parametrize(
    "field,value",
    [
        ("max_context_characters", 0),
        ("relevant_file_limit", 0),
        ("relevant_code_limit", 0),
        ("memory_limit", 0),
        ("memory_limit", True),
    ],
)
def test_invalid_limits_are_rejected(
    service,
    dependencies,
    field,
    value,
):
    with pytest.raises(ReasoningOrchestrationError):
        run_answer(
            service,
            dependencies["tmp_path"],
            **{field: value},
        )


def test_non_callable_ai_service_factory_is_rejected(dependencies):
    mocks = dependencies["mocks"]

    with pytest.raises(ReasoningOrchestrationError):
        ReasoningOrchestrationService(
            repository_retrieval_service=mocks[
                "repository_retrieval_service"
            ],
            relevant_file_retrieval_service=mocks[
                "relevant_file_retrieval_service"
            ],
            relevant_code_retrieval_service=mocks[
                "relevant_code_retrieval_service"
            ],
            dependency_context_service=mocks[
                "dependency_context_service"
            ],
            architecture_context_service=mocks[
                "architecture_context_service"
            ],
            ai_service_factory="not-callable",
        )


def test_non_callable_reasoning_service_factory_is_rejected(dependencies):
    mocks = dependencies["mocks"]

    with pytest.raises(
        ReasoningOrchestrationError,
        match="Reasoning service factory must be callable",
    ):
        ReasoningOrchestrationService(
            repository_retrieval_service=mocks[
                "repository_retrieval_service"
            ],
            relevant_file_retrieval_service=mocks[
                "relevant_file_retrieval_service"
            ],
            relevant_code_retrieval_service=mocks[
                "relevant_code_retrieval_service"
            ],
            dependency_context_service=mocks[
                "dependency_context_service"
            ],
            architecture_context_service=mocks[
                "architecture_context_service"
            ],
            ai_service_factory=mocks["ai_service_factory"],
            reasoning_service_factory="not-callable",
        )


def test_discovery_failure_is_wrapped(
    service,
    dependencies,
):
    mocks = dependencies["mocks"]

    mocks["repository_discovery_service"].discover.side_effect = (
        RuntimeError("Discovery failed")
    )

    with pytest.raises(
        ReasoningOrchestrationError,
        match="Unable to complete repository reasoning",
    ):
        run_answer(service, dependencies["tmp_path"])


def test_context_builder_failure_is_wrapped(
    service,
    dependencies,
):
    mocks = dependencies["mocks"]

    mocks["context_builder"].build_context.side_effect = (
        ValueError("Context failure")
    )

    with pytest.raises(
        ReasoningOrchestrationError,
        match="Unable to complete repository reasoning",
    ):
        run_answer(service, dependencies["tmp_path"])


def test_response_contains_context_source_references(
    service,
    dependencies,
):
    dependencies["combined_context"].source_files = (
        "app/main.py",
        "app/services/user.py",
    )

    dependencies["combined_context"].entity_ids = (
        "entity-1",
        "entity-2",
    )

    response = run_answer(
        service,
        dependencies["tmp_path"],
    )

    assert response.source_files == (
        "app/main.py",
        "app/services/user.py",
    )

    assert response.entity_ids == (
        "entity-1",
        "entity-2",
    )
