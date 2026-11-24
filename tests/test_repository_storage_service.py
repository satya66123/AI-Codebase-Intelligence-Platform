
import json

import pytest

from app.application.repository_storage_service import (
    RepositoryStorageService,
    RepositoryStorageError,
)


@pytest.fixture
def sample_index():
    return {
        "repository_name": "test_repository",
        "repository_path": "C:/projects/test_repository",
        "total_files": 2,
        "total_directories": 1,
        "total_size_bytes": 150,
        "languages": {
            "Python": 1,
            "JavaScript": 1,
        },
        "files": [
            {
                "name": "main.py",
                "relative_path": "main.py",
                "extension": ".py",
                "language": "Python",
                "size_bytes": 100,
                "modified_time": "2026-11-24T10:00:00",
            },
            {
                "name": "app.js",
                "relative_path": "app.js",
                "extension": ".js",
                "language": "JavaScript",
                "size_bytes": 50,
                "modified_time": "2026-11-24T10:00:00",
            },
        ],
    }


def test_save_repository_index(tmp_path, sample_index):
    service = RepositoryStorageService(tmp_path)

    result = service.save_index(sample_index)

    assert result.exists()
    assert result.name == "test_repository.json"


def test_load_repository_index(tmp_path, sample_index):
    service = RepositoryStorageService(tmp_path)

    service.save_index(sample_index)

    loaded = service.load_index("test_repository")

    assert loaded == sample_index


def test_saved_index_is_valid_json(tmp_path, sample_index):
    service = RepositoryStorageService(tmp_path)

    path = service.save_index(sample_index)

    with path.open("r", encoding="utf-8") as file:
        loaded = json.load(file)

    assert loaded["repository_name"] == "test_repository"
    assert loaded["total_files"] == 2


def test_delete_repository_index(tmp_path, sample_index):
    service = RepositoryStorageService(tmp_path)

    service.save_index(sample_index)

    result = service.delete_index("test_repository")

    assert result is True
    assert not (tmp_path / "test_repository.json").exists()


def test_delete_missing_index_returns_false(tmp_path):
    service = RepositoryStorageService(tmp_path)

    assert service.delete_index("missing") is False


def test_list_repository_indexes(tmp_path, sample_index):
    service = RepositoryStorageService(tmp_path)

    service.save_index(sample_index)

    second_index = dict(sample_index)
    second_index["repository_name"] = "another_repository"

    service.save_index(second_index)

    result = service.list_indexes()

    assert result == [
        "another_repository",
        "test_repository",
    ]


def test_load_missing_index_rejected(tmp_path):
    service = RepositoryStorageService(tmp_path)

    with pytest.raises(RepositoryStorageError):
        service.load_index("missing")


def test_invalid_repository_name_rejected(tmp_path):
    service = RepositoryStorageService(tmp_path)

    with pytest.raises(RepositoryStorageError):
        service.load_index("../outside")
