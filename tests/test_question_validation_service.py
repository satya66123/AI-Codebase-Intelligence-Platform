
import pytest

from app.application.question_validation_service import (
    QuestionValidationError,
    QuestionValidationService,
    ValidatedQuestion,
)


@pytest.fixture
def service():
    return QuestionValidationService()


def test_service_initialization():
    service = QuestionValidationService(max_length=500)

    assert service.max_length == 500


@pytest.mark.parametrize("max_length", [0, -1, 1.5, True, None, "100"])
def test_service_rejects_invalid_max_length(max_length):
    with pytest.raises(QuestionValidationError):
        QuestionValidationService(max_length=max_length)



def test_validate_valid_question(service):
    result = service.validate(
        "Where is authentication implemented?"
    )

    assert isinstance(result, ValidatedQuestion)
    assert result.question == "Where is authentication implemented?"
    assert result.character_count == 36



def test_validate_removes_surrounding_whitespace(service):
    result = service.validate(
        "   Explain the project architecture.   "
    )

    assert result.question == "Explain the project architecture."
    assert result.character_count == len(result.question)


@pytest.mark.parametrize(
    "question",
    [
        "",
        " ",
        "   ",
        "\n\t ",
    ],
)
def test_validate_rejects_empty_questions(service, question):
    with pytest.raises(
        QuestionValidationError,
        match="Question cannot be empty",
    ):
        service.validate(question)


@pytest.mark.parametrize(
    "question",
    [
        None,
        123,
        12.5,
        True,
        [],
        {},
    ],
)
def test_validate_rejects_non_string_questions(service, question):
    with pytest.raises(
        QuestionValidationError,
        match="Question must be a string",
    ):
        service.validate(question)


def test_validate_rejects_question_exceeding_maximum_length():
    service = QuestionValidationService(max_length=10)

    with pytest.raises(
        QuestionValidationError,
        match="exceeds the maximum length",
    ):
        service.validate("This question is too long")


def test_validate_accepts_question_at_maximum_length():
    service = QuestionValidationService(max_length=10)

    result = service.validate("1234567890")

    assert result.question == "1234567890"
    assert result.character_count == 10


def test_validate_rejects_null_character(service):
    with pytest.raises(
        QuestionValidationError,
        match="null characters",
    ):
        service.validate("Explain\x00 this code")


def test_validate_preserves_internal_whitespace(service):
    question = "Explain the data flow\nfrom API to storage."

    result = service.validate(question)

    assert result.question == question


def test_validate_preserves_unicode_question(service):
    question = "Explain this Python module — വിശദീകരിക്കുക"

    result = service.validate(question)

    assert result.question == question


def test_validated_question_rejects_invalid_text():
    with pytest.raises(QuestionValidationError):
        ValidatedQuestion(
            question=" ",
            character_count=1,
        )


def test_validated_question_rejects_incorrect_character_count():
    with pytest.raises(QuestionValidationError):
        ValidatedQuestion(
            question="Explain this function",
            character_count=10,
        )
