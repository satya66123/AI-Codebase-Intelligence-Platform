
import pytest

from app.application.repository_agent import RepositoryAgent
from app.application.repository_input import RepositoryInputError
from app.application.repository_storage_service import (
    RepositoryStorageService,
)


@pytest.fixture
def repository_agent(tmp_path):
    storage = RepositoryStorageService(
        storage_directory=tmp_path / "storage"
    )

    return RepositoryAgent(
        storage_service=storage
    )


@pytest.fixture
def sample_repository(tmp_path):
    repository = tmp_path / "sample_project"
    repository.mkdir()

    (repository / "main.py").write_text(
        "print('hello')",
        encoding="utf-8",
    )

    (repository / "app.js").write_text(
        "console.log('hello')",
        encoding="utf-8",
    )

    source = repository / "src"
    source.mkdir()

    (source / "service.py").write_text(
        "class Service: pass",
        encoding="utf-8",
    )

    return repository


def test_repository_agent_discovers_repository(
    repository_agent,
    sample_repository,
):
    result = repository_agent.discover_repository(
        sample_repository
    )

    assert result.repository.name == "sample_project"
    assert result.metadata["total_files"] == 3
    assert result.metadata["total_directories"] == 1


def test_repository_agent_generates_repository_map(
    repository_agent,
    sample_repository,
):
    result = repository_agent.discover_repository(
        sample_repository
    )

    assert "sample_project" in result.repository_map
    assert "main.py" in result.repository_map
    assert "service.py" in result.repository_map


def test_repository_agent_extracts_language_metadata(
    repository_agent,
    sample_repository,
):
    result = repository_agent.discover_repository(
        sample_repository
    )

    assert result.metadata["languages"] == {
        "JavaScript": 1,
        "Python": 2,
    }


def test_repository_agent_builds_searchable_index(
    repository_agent,
    sample_repository,
):
    result = repository_agent.discover_repository(
        sample_repository
    )

    assert result.index["total_files"] == 3
    assert len(result.index["files"]) == 3


def test_repository_agent_applies_ignore_rules(
    repository_agent,
    sample_repository,
):
    (sample_repository / "cache.pyc").write_text(
        "compiled",
        encoding="utf-8",
    )

    result = repository_agent.discover_repository(
        sample_repository
    )

    discovered_names = {
        path.name for path in result.scan_result.files
    }

    assert "cache.pyc" not in discovered_names
    assert "main.py" in discovered_names


def test_repository_agent_saves_index(
    repository_agent,
    sample_repository,
):
    result = repository_agent.discover_repository(
        sample_repository
    )

    assert result.storage_path is not None
    assert result.storage_path.exists()

    stored_index = repository_agent.storage_service.load_index(
        "sample_project"
    )

    assert stored_index["total_files"] == 3


def test_repository_agent_can_skip_storage(
    repository_agent,
    sample_repository,
):
    result = repository_agent.discover_repository(
        sample_repository,
        save_index=False,
    )

    assert result.storage_path is None
    assert repository_agent.storage_service.list_indexes() == []


def test_repository_agent_rejects_invalid_repository(
    repository_agent,
    tmp_path,
):
    missing_path = tmp_path / "missing_repository"

    with pytest.raises(RepositoryInputError):
        repository_agent.discover_repository(missing_path)
