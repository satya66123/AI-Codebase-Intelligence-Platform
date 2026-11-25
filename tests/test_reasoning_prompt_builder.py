
import pytest

from app.application.context_builder import ContextBuildResult
from app.application.intent_detection_service import QueryIntent
from app.application.reasoning_prompt_builder import (
    ReasoningPromptBuilder,
    ReasoningPromptBuilderError,
)


QUESTION = "Explain the UserService class."


@pytest.fixture
def builder():
    return ReasoningPromptBuilder()


@pytest.fixture
def context():
    context_text = (
        "Repository: sample-project\n"
        "File: app/services/user_service.py\n"
        "Class: UserService\n"
        "Method: create_user"
    )

    return ContextBuildResult(
        question=QUESTION,
        intent=QueryIntent.CODE_EXPLANATION,
        sections=(),
        context_text=context_text,
        source_files=("app/services/user_service.py",),
        entity_ids=("user-service",),
        character_count=len(context_text),
        max_characters=12000,
        truncated=False,
    )


def test_builder_initialization(builder):
    assert isinstance(builder, ReasoningPromptBuilder)


def test_build_prompt_returns_string(builder, context):
    result = builder.build_prompt(
        QUESTION,
        QueryIntent.CODE_EXPLANATION,
        context,
    )

    assert isinstance(result, str)
    assert result.strip()


def test_prompt_contains_user_question(builder, context):
    result = builder.build_prompt(
        QUESTION,
        QueryIntent.CODE_EXPLANATION,
        context,
    )

    assert QUESTION in result


def test_prompt_contains_intent(builder, context):
    result = builder.build_prompt(
        QUESTION,
        QueryIntent.CODE_EXPLANATION,
        context,
    )

    assert "CODE_EXPLANATION" in result


def test_prompt_contains_repository_context(builder, context):
    result = builder.build_prompt(
        QUESTION,
        QueryIntent.CODE_EXPLANATION,
        context,
    )

    assert "UserService" in result
    assert "create_user" in result
    assert "sample-project" in result


def test_prompt_contains_source_files(builder, context):
    result = builder.build_prompt(
        QUESTION,
        QueryIntent.CODE_EXPLANATION,
        context,
    )

    assert "app/services/user_service.py" in result


def test_prompt_contains_entity_ids(builder, context):
    result = builder.build_prompt(
        QUESTION,
        QueryIntent.CODE_EXPLANATION,
        context,
    )

    assert "user-service" in result


def test_prompt_contains_evidence_rules(builder, context):
    result = builder.build_prompt(
        QUESTION,
        QueryIntent.CODE_EXPLANATION,
        context,
    )

    assert "Never invent" in result
    assert "evidence" in result.lower()


def test_prompt_marks_context_as_untrusted(builder, context):
    result = builder.build_prompt(
        QUESTION,
        QueryIntent.CODE_EXPLANATION,
        context,
    )

    assert "untrusted data" in result


def test_prompt_contains_context_tags(builder, context):
    result = builder.build_prompt(
        QUESTION,
        QueryIntent.CODE_EXPLANATION,
        context,
    )

    assert "<repository_context>" in result
    assert "</repository_context>" in result


def test_prompt_contains_execution_safety_rule(builder, context):
    result = builder.build_prompt(
        QUESTION,
        QueryIntent.CODE_EXPLANATION,
        context,
    )

    assert "Do not claim to have executed" in result


@pytest.mark.parametrize(
    "intent",
    [
        QueryIntent.ARCHITECTURE,
        QueryIntent.FILE_LOCATION,
        QueryIntent.CODE_EXPLANATION,
        QueryIntent.DEPENDENCY,
        QueryIntent.CALL_RELATIONSHIP,
        QueryIntent.DATA_FLOW,
        QueryIntent.EXECUTION_FLOW,
        QueryIntent.CHANGE_IMPACT,
        QueryIntent.CONFIGURATION,
        QueryIntent.GENERAL_CODEBASE,
        QueryIntent.UNKNOWN,
    ],
)
def test_supports_all_query_intents(builder, context, intent):
    result = builder.build_prompt(
        QUESTION,
        intent,
        context,
    )

    assert intent.name in result
    assert result.strip()


@pytest.mark.parametrize(
    "question",
    [
        "",
        " ",
        None,
        123,
    ],
)
def test_rejects_invalid_question(builder, context, question):
    with pytest.raises(ReasoningPromptBuilderError):
        builder.build_prompt(
            question,
            QueryIntent.CODE_EXPLANATION,
            context,
        )


@pytest.mark.parametrize(
    "intent",
    [
        None,
        "CODE_EXPLANATION",
        "unknown",
        123,
    ],
)
def test_rejects_invalid_intent(builder, context, intent):
    with pytest.raises(ReasoningPromptBuilderError):
        builder.build_prompt(
            QUESTION,
            intent,
            context,
        )


@pytest.mark.parametrize(
    "invalid_context",
    [
        None,
        "invalid",
        {},
    ],
)
def test_rejects_invalid_context(builder, invalid_context):
    with pytest.raises(ReasoningPromptBuilderError):
        builder.build_prompt(
            QUESTION,
            QueryIntent.CODE_EXPLANATION,
            invalid_context,
        )


def test_rejects_empty_context_text(builder):
    empty_context = ContextBuildResult(
        question=QUESTION,
        intent=QueryIntent.CODE_EXPLANATION,
        sections=(),
        context_text=" ",
        source_files=(),
        entity_ids=(),
        character_count=1,
        max_characters=12000,
        truncated=False,
    )

    with pytest.raises(
        ReasoningPromptBuilderError,
        match="Context text cannot be empty",
    ):
        builder.build_prompt(
            QUESTION,
            QueryIntent.CODE_EXPLANATION,
            empty_context,
        )


def test_rejects_question_mismatch(builder, context):
    with pytest.raises(
        ReasoningPromptBuilderError,
        match="Question must match",
    ):
        builder.build_prompt(
            "Explain the database layer.",
            QueryIntent.CODE_EXPLANATION,
            context,
        )


def test_strips_question_whitespace(builder, context):
    result = builder.build_prompt(
        f"  {QUESTION}  ",
        QueryIntent.CODE_EXPLANATION,
        context,
    )

    assert QUESTION in result


def test_empty_source_files_are_supported(builder):
    context = ContextBuildResult(
        question=QUESTION,
        intent=QueryIntent.CODE_EXPLANATION,
        sections=(),
        context_text="Repository context",
        source_files=(),
        entity_ids=(),
        character_count=len("Repository context"),
        max_characters=12000,
        truncated=False,
    )

    result = builder.build_prompt(
        QUESTION,
        QueryIntent.CODE_EXPLANATION,
        context,
    )

    assert "Source files: None supplied." in result


def test_empty_entity_ids_are_supported(builder):
    context = ContextBuildResult(
        question=QUESTION,
        intent=QueryIntent.CODE_EXPLANATION,
        sections=(),
        context_text="Repository context",
        source_files=(),
        entity_ids=(),
        character_count=len("Repository context"),
        max_characters=12000,
        truncated=False,
    )

    result = builder.build_prompt(
        QUESTION,
        QueryIntent.CODE_EXPLANATION,
        context,
    )

    assert "Code entity IDs: None supplied." in result


def test_multiple_source_files_are_included(builder):
    context = ContextBuildResult(
        question=QUESTION,
        intent=QueryIntent.CODE_EXPLANATION,
        sections=(),
        context_text="Repository context",
        source_files=(
            "app/services/user_service.py",
            "app/models/user.py",
        ),
        entity_ids=(),
        character_count=len("Repository context"),
        max_characters=12000,
        truncated=False,
    )

    result = builder.build_prompt(
        QUESTION,
        QueryIntent.CODE_EXPLANATION,
        context,
    )

    assert "app/services/user_service.py" in result
    assert "app/models/user.py" in result


def test_truncated_context_is_identified(builder):
    context_text = "Repository context"

    context = ContextBuildResult(
        question=QUESTION,
        intent=QueryIntent.CODE_EXPLANATION,
        sections=(),
        context_text=context_text,
        source_files=(),
        entity_ids=(),
        character_count=len(context_text),
        max_characters=12000,
        truncated=True,
    )

    result = builder.build_prompt(
        QUESTION,
        QueryIntent.CODE_EXPLANATION,
        context,
    )

    assert "was truncated" in result
    assert "omitted information" in result


def test_non_truncated_context_is_identified(builder, context):
    result = builder.build_prompt(
        QUESTION,
        QueryIntent.CODE_EXPLANATION,
        context,
    )

    assert "was not truncated" in result


def test_prompt_is_deterministic(builder, context):
    first = builder.build_prompt(
        QUESTION,
        QueryIntent.CODE_EXPLANATION,
        context,
    )

    second = builder.build_prompt(
        QUESTION,
        QueryIntent.CODE_EXPLANATION,
        context,
    )

    assert first == second


def test_prompt_does_not_modify_context(builder, context):
    original = context.context_text

    builder.build_prompt(
        QUESTION,
        QueryIntent.CODE_EXPLANATION,
        context,
    )

    assert context.context_text == original


def test_architecture_intent_has_architecture_instructions(
    builder,
    context,
):
    result = builder.build_prompt(
        QUESTION,
        QueryIntent.ARCHITECTURE,
        context,
    )

    assert "architecture" in result.lower()
    assert "directory structure" in result.lower()


def test_dependency_intent_has_dependency_instructions(
    builder,
    context,
):
    result = builder.build_prompt(
        QUESTION,
        QueryIntent.DEPENDENCY,
        context,
    )

    assert "dependencies" in result.lower()
    assert "standard-library" in result.lower()


def test_call_relationship_intent_has_call_instructions(
    builder,
    context,
):
    result = builder.build_prompt(
        QUESTION,
        QueryIntent.CALL_RELATIONSHIP,
        context,
    )

    assert "call relationships" in result.lower()
    assert "call graph" in result.lower()


def test_change_impact_intent_has_impact_instructions(
    builder,
    context,
):
    result = builder.build_prompt(
        QUESTION,
        QueryIntent.CHANGE_IMPACT,
        context,
    )

    assert "potential impacts" in result.lower()
    assert "dependencies" in result.lower()


def test_unknown_intent_uses_cautious_instructions(
    builder,
    context,
):
    result = builder.build_prompt(
        QUESTION,
        QueryIntent.UNKNOWN,
        context,
    )

    assert "cautiously" in result.lower()
    assert "cannot be answered" in result.lower()


def test_prompt_does_not_claim_code_execution(builder, context):
    result = builder.build_prompt(
        QUESTION,
        QueryIntent.CODE_EXPLANATION,
        context,
    )

    assert "executed or tested" in result
