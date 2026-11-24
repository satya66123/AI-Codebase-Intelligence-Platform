
import pytest

from app.application.repository_input import (
    RepositoryInputError,
    validate_repository_path,
)

def test_valid_repository_path(tmp_path):
    (tmp_path / "README.md").write_text("# Test Repository")

    result = validate_repository_path(tmp_path)

    assert result.root == tmp_path.resolve()
    assert result.name == tmp_path.name
    assert result.is_git_repository is False

def test_git_repository_detection(tmp_path):
    (tmp_path / ".git").mkdir()
    (tmp_path / "README.md").write_text("# Git Repository")

    result = validate_repository_path(tmp_path)

    assert result.is_git_repository is True

def test_string_path_input(tmp_path):
    (tmp_path / "main.py").write_text("print('hello')")

    result = validate_repository_path(str(tmp_path))

    assert result.root == tmp_path.resolve()

def test_none_path_rejected():
    with pytest.raises(RepositoryInputError) as error:
        validate_repository_path(None)

    assert error.value.code == "EMPTY_PATH"

def test_empty_path_rejected():
    with pytest.raises(RepositoryInputError):
        validate_repository_path("")

def test_missing_path_rejected(tmp_path):
    with pytest.raises(RepositoryInputError) as error:
        validate_repository_path(tmp_path / "missing")

    assert error.value.code == "PATH_RESOLUTION_FAILED"

def test_file_path_rejected(tmp_path):
    file_path = tmp_path / "file.txt"
    file_path.write_text("test")

    with pytest.raises(RepositoryInputError) as error:
        validate_repository_path(file_path)

    assert error.value.code == "NOT_A_DIRECTORY"

def test_empty_repository_rejected(tmp_path):
    with pytest.raises(RepositoryInputError) as error:
        validate_repository_path(tmp_path)

    assert error.value.code == "EMPTY_REPOSITORY"