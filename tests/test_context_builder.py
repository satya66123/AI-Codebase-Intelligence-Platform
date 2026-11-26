
import pytest

from appy.application.intent_detection_service import QueryIntent
from appy.application.question_analysis_agent import (
    QuestionAnalysisResult,
)
from appy.application.repository_retrieval_service import (
    RepositoryRetrievalResult,
)
from appy.application.relevant_file_retrieval_service import (
    RelevantFile,
    RelevantFileRetrievalResult,
)
from appy.application.relevant_code_retrieval_service import (
    RelevantCodeRetrievalResult,
)
from appy.application.code_indexing_service import CodeIndexEntry
from appy.application.dependency_context_service import (
    DependencyContextResult,
)
from appy.application.architecture_context_service import (
    ArchitectureContextResult,
)
from appy.application.context_builder import (
    ContextBuilder,
    ContextBuilderError,
    ContextBuildResult,
    ContextSection,
)


QUESTION = "Where is authentication implemented?"


@pytest.fixture
def question_analysis():
    return QuestionAnalysisResult(
        question=QUESTION,
        intent=QueryIntent.CODE_EXPLANATION,
        confidence=0.9,
        matched_terms=("authentication",),
    )


@pytest.fixture
def repository_result():
    return RepositoryRetrievalResult(
        repository_id="repo-1",
        question=QUESTION,
        intent=QueryIntent.CODE_EXPLANATION,
        retrieval_data={
            "repository_name": "sample-repository",
            "description": "A sample Python repository.",
        },
    )


@pytest.fixture
def code_entry():
    return CodeIndexEntry(
        entity_id="entity-1",
        name="authenticate_user",
        entity_type="function",
        qualified_name="auth.authenticate_user",
        filename="appy/auth.py",
        line=10,
        end_line=20,
        parent=None,
        docstring="Authenticate a user.",
        normalized_name="authenticate_user",
        search_text="authenticate_user authentication appy/auth.py",
    )


@pytest.fixture
def relevant_files(code_entry):
    return RelevantFileRetrievalResult(
        question=QUESTION,
        total_files=1,
        files=(
            RelevantFile(
                filename="appy/auth.py",
                relevance_score=1,
                matched_entities=(code_entry,),
            ),
        ),
    )


@pytest.fixture
def relevant_code(code_entry):
    return RelevantCodeRetrievalResult(
        question=QUESTION,
        total_code_entities=1,
        code_entities=(code_entry,),
    )


@pytest.fixture
def dependency_context():
    return DependencyContextResult(
        total_dependencies=0,
        dependencies=(),
        dependencies_by_file={},
        dependency_counts={
            "internal": 0,
            "external": 0,
            "standard_library": 0,
            "unresolved": 0,
        },
    )


@pytest.fixture
def architecture_context():
    return ArchitectureContextResult(
        repository_name="sample-repository",
        repository_root="/repositories/sample-repository",
        is_git_repository=True,
        directory_tree="sample-repository\n└── appy",
        call_graphs=(),
        inheritance_analyses=(),
        total_calls=0,
        total_inheritance_relationships=0,
        classes_without_bases=(),
    )


@pytest.fixture
def builder():
    return ContextBuilder()


@pytest.fixture
def build_inputs(
    question_analysis,
    repository_result,
    relevant_files,
    relevant_code,
    dependency_context,
    architecture_context,
):
    return {
        "question_analysis": question_analysis,
        "repository_result": repository_result,
        "relevant_files": relevant_files,
        "relevant_code": relevant_code,
        "dependency_context": dependency_context,
        "architecture_context": architecture_context,
    }


# ---------------------------------------------------------
# Context section tests
# ---------------------------------------------------------


def test_context_section_creation():
    section = ContextSection(
        name="relevant_code",
        content="Authentication function.",
        source_files=("appy/auth.py",),
        entity_ids=("entity-1",),
    )

    assert section.name == "relevant_code"
    assert section.content == "Authentication function."


def test_context_section_rejects_empty_name():
    with pytest.raises(ContextBuilderError):
        ContextSection(
            name="",
            content="content",
        )


def test_context_section_rejects_non_string_content():
    with pytest.raises(ContextBuilderError):
        ContextSection(
            name="code",
            content=123,
        )


def test_context_section_rejects_non_tuple_source_files():
    with pytest.raises(ContextBuilderError):
        ContextSection(
            name="code",
            content="content",
            source_files=["appy/auth.py"],
        )


def test_context_section_rejects_empty_source_filename():
    with pytest.raises(ContextBuilderError):
        ContextSection(
            name="code",
            content="content",
            source_files=("",),
        )


def test_context_section_rejects_non_tuple_entity_ids():
    with pytest.raises(ContextBuilderError):
        ContextSection(
            name="code",
            content="content",
            entity_ids=["entity-1"],
        )


def test_context_section_rejects_empty_entity_id():
    with pytest.raises(ContextBuilderError):
        ContextSection(
            name="code",
            content="content",
            entity_ids=("",),
        )


# ---------------------------------------------------------
# Context build result tests
# ---------------------------------------------------------


def test_context_build_result_creation():
    result = ContextBuildResult(
        question=QUESTION,
        intent="code_explanation",
        sections=(),
        context_text="",
        source_files=(),
        entity_ids=(),
        character_count=0,
        max_characters=100,
        truncated=False,
    )

    assert result.question == QUESTION
    assert result.character_count == 0


def test_context_result_rejects_empty_question():
    with pytest.raises(ContextBuilderError):
        ContextBuildResult(
            question="",
            intent="code_explanation",
            sections=(),
            context_text="",
            source_files=(),
            entity_ids=(),
            character_count=0,
            max_characters=100,
            truncated=False,
        )


def test_context_result_rejects_empty_intent():
    with pytest.raises(ContextBuilderError):
        ContextBuildResult(
            question=QUESTION,
            intent="",
            sections=(),
            context_text="",
            source_files=(),
            entity_ids=(),
            character_count=0,
            max_characters=100,
            truncated=False,
        )


def test_context_result_rejects_non_tuple_sections():
    with pytest.raises(ContextBuilderError):
        ContextBuildResult(
            question=QUESTION,
            intent="code_explanation",
            sections=[],
            context_text="",
            source_files=(),
            entity_ids=(),
            character_count=0,
            max_characters=100,
            truncated=False,
        )


def test_context_result_rejects_invalid_section():
    with pytest.raises(ContextBuilderError):
        ContextBuildResult(
            question=QUESTION,
            intent="code_explanation",
            sections=("invalid",),
            context_text="",
            source_files=(),
            entity_ids=(),
            character_count=0,
            max_characters=100,
            truncated=False,
        )


def test_context_result_rejects_character_count_mismatch():
    with pytest.raises(ContextBuilderError):
        ContextBuildResult(
            question=QUESTION,
            intent="code_explanation",
            sections=(),
            context_text="hello",
            source_files=(),
            entity_ids=(),
            character_count=2,
            max_characters=100,
            truncated=False,
        )


def test_context_result_rejects_exceeding_maximum():
    with pytest.raises(ContextBuilderError):
        ContextBuildResult(
            question=QUESTION,
            intent="code_explanation",
            sections=(),
            context_text="hello",
            source_files=(),
            entity_ids=(),
            character_count=5,
            max_characters=3,
            truncated=False,
        )


# ---------------------------------------------------------
# Context builder initialization
# ---------------------------------------------------------


def test_builder_initialization():
    assert ContextBuilder() is not None


# ---------------------------------------------------------
# Successful context construction
# ---------------------------------------------------------


def test_build_context_returns_result(builder, build_inputs):
    result = builder.build_context(**build_inputs)

    assert isinstance(result, ContextBuildResult)


def test_build_context_preserves_question(builder, build_inputs):
    result = builder.build_context(**build_inputs)

    assert result.question == QUESTION


def test_build_context_preserves_intent(builder, build_inputs):
    result = builder.build_context(**build_inputs)

    assert result.intent == "code_explanation"


def test_build_context_creates_repository_section(
    builder,
    build_inputs,
):
    result = builder.build_context(**build_inputs)

    names = [section.name for section in result.sections]

    assert "repository_intelligence" in names


def test_build_context_creates_relevant_files_section(
    builder,
    build_inputs,
):
    result = builder.build_context(**build_inputs)

    names = [section.name for section in result.sections]

    assert "relevant_files" in names


def test_build_context_creates_relevant_code_section(
    builder,
    build_inputs,
):
    result = builder.build_context(**build_inputs)

    names = [section.name for section in result.sections]

    assert "relevant_code" in names


def test_build_context_creates_dependency_section(
    builder,
    build_inputs,
):
    result = builder.build_context(**build_inputs)

    names = [section.name for section in result.sections]

    assert "dependency_context" in names


def test_build_context_creates_architecture_section(
    builder,
    build_inputs,
):
    result = builder.build_context(**build_inputs)

    names = [section.name for section in result.sections]

    assert "architecture_context" in names


def test_build_context_contains_all_five_sections(
    builder,
    build_inputs,
):
    result = builder.build_context(**build_inputs)

    assert len(result.sections) == 5


def test_build_context_generates_text(
    builder,
    build_inputs,
):
    result = builder.build_context(**build_inputs)

    assert "repository_intelligence" in result.context_text
    assert "relevant_code" in result.context_text


def test_build_context_generates_json_section_content(
    builder,
    build_inputs,
):
    result = builder.build_context(**build_inputs)

    for section in result.sections:
        assert isinstance(section.content, str)
        assert section.content


# ---------------------------------------------------------
# Source reference tests
# ---------------------------------------------------------


def test_build_context_collects_source_files(
    builder,
    build_inputs,
):
    result = builder.build_context(**build_inputs)

    assert "appy/auth.py" in result.source_files


def test_build_context_collects_entity_ids(
    builder,
    build_inputs,
):
    result = builder.build_context(**build_inputs)

    assert "entity-1" in result.entity_ids


def test_build_context_deduplicates_source_files(
    builder,
    build_inputs,
):
    result = builder.build_context(**build_inputs)

    assert len(result.source_files) == len(
        set(result.source_files)
    )


def test_build_context_deduplicates_entity_ids(
    builder,
    build_inputs,
):
    result = builder.build_context(**build_inputs)

    assert len(result.entity_ids) == len(
        set(result.entity_ids)
    )


# ---------------------------------------------------------
# Character limit tests
# ---------------------------------------------------------


def test_build_context_uses_default_character_limit(
    builder,
    build_inputs,
):
    result = builder.build_context(**build_inputs)

    assert result.max_characters == 12000


def test_build_context_accepts_custom_character_limit(
    builder,
    build_inputs,
):
    result = builder.build_context(
        **build_inputs,
        max_characters=20000,
    )

    assert result.max_characters == 20000


def test_build_context_never_exceeds_character_limit(
    builder,
    build_inputs,
):
    result = builder.build_context(
        **build_inputs,
        max_characters=1000,
    )

    assert result.character_count <= 1000


def test_build_context_reports_character_count(
    builder,
    build_inputs,
):
    result = builder.build_context(**build_inputs)

    assert result.character_count == len(result.context_text)


def test_build_context_reports_truncation(
    builder,
    build_inputs,
):
    result = builder.build_context(
        **build_inputs,
        max_characters=100,
    )

    assert result.truncated is True


def test_build_context_does_not_report_truncation_when_context_fits(
    builder,
    build_inputs,
):
    result = builder.build_context(
        **build_inputs,
        max_characters=20000,
    )

    assert result.truncated is False


def test_build_context_rejects_zero_character_limit(
    builder,
    build_inputs,
):
    with pytest.raises(ContextBuilderError):
        builder.build_context(
            **build_inputs,
            max_characters=0,
        )


def test_build_context_rejects_negative_character_limit(
    builder,
    build_inputs,
):
    with pytest.raises(ContextBuilderError):
        builder.build_context(
            **build_inputs,
            max_characters=-1,
        )


def test_build_context_rejects_boolean_character_limit(
    builder,
    build_inputs,
):
    with pytest.raises(ContextBuilderError):
        builder.build_context(
            **build_inputs,
            max_characters=True,
        )


# ---------------------------------------------------------
# Input validation tests
# ---------------------------------------------------------


@pytest.mark.parametrize(
    "field",
    [
        "question_analysis",
        "repository_result",
        "relevant_files",
        "relevant_code",
        "dependency_context",
        "architecture_context",
    ],
)
def test_build_context_rejects_invalid_input(
    builder,
    build_inputs,
    field,
):
    build_inputs[field] = "invalid"

    with pytest.raises(ContextBuilderError):
        builder.build_context(**build_inputs)


def test_build_context_rejects_question_mismatch(
    builder,
    build_inputs,
):
    build_inputs["relevant_files"] = RelevantFileRetrievalResult(
        question="A different question",
        total_files=0,
        files=(),
    )

    with pytest.raises(ContextBuilderError):
        builder.build_context(**build_inputs)


def test_build_context_rejects_repository_question_mismatch(
    builder,
    build_inputs,
):
    build_inputs["repository_result"] = RepositoryRetrievalResult(
        repository_id="repo-1",
        question="A different question",
        intent=QueryIntent.CODE_EXPLANATION,
        retrieval_data={},
    )

    with pytest.raises(ContextBuilderError):
        builder.build_context(**build_inputs)


def test_build_context_rejects_code_question_mismatch(
    builder,
    build_inputs,
):
    build_inputs["relevant_code"] = RelevantCodeRetrievalResult(
        question="A different question",
        total_code_entities=0,
        code_entities=(),
    )

    with pytest.raises(ContextBuilderError):
        builder.build_context(**build_inputs)


# ---------------------------------------------------------
# Deterministic output tests
# ---------------------------------------------------------


def test_build_context_is_deterministic(
    builder,
    build_inputs,
):
    first = builder.build_context(**build_inputs)
    second = builder.build_context(**build_inputs)

    assert first.context_text == second.context_text


def test_build_context_preserves_section_order(
    builder,
    build_inputs,
):
    result = builder.build_context(**build_inputs)

    names = tuple(
        section.name for section in result.sections
    )

    assert names == (
        "repository_intelligence",
        "relevant_files",
        "relevant_code",
        "dependency_context",
        "architecture_context",
    )


def test_build_context_preserves_entity_identity(
    builder,
    build_inputs,
):
    result = builder.build_context(**build_inputs)

    code_section = next(
        section
        for section in result.sections
        if section.name == "relevant_code"
    )

    assert code_section.entity_ids == ("entity-1",)
    assert code_section.source_files == ("appy/auth.py",)
