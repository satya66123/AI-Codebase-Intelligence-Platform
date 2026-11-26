
import pytest

from appy.application.repository_input import RepositoryInfo
from appy.application.repository_scanner import (
    RepositoryScanError,
)
from appy.application.file_discovery_service import (
    FileDiscoveryService,
)


def create_repository(root):
    return RepositoryInfo(
        root=root,
        name=root.name,
        is_git_repository=False
    )


def test_discover_repository_files(tmp_path):
    (tmp_path / "main.py").write_text("print('hello')")
    (tmp_path / "README.md").write_text("# Project")

    service = FileDiscoveryService()
    result = service.discover(create_repository(tmp_path))

    assert result.total_files == 2
    assert {path.name for path in result.files} == {
        "main.py",
        "README.md"
    }


def test_discover_nested_repository_files(tmp_path):
    source = tmp_path / "src"
    source.mkdir()

    (source / "main.py").write_text("print('hello')")

    service = FileDiscoveryService()
    result = service.discover(create_repository(tmp_path))

    assert result.total_files == 1
    assert result.total_directories == 1


def test_discover_empty_repository(tmp_path):
    service = FileDiscoveryService()
    result = service.discover(create_repository(tmp_path))

    assert result.total_files == 0
    assert result.total_directories == 0


def test_discovery_statistics(tmp_path):
    (tmp_path / "main.py").write_text("print('hello')")

    source = tmp_path / "src"
    source.mkdir()

    service = FileDiscoveryService()
    result = service.discover(create_repository(tmp_path))

    statistics = service.get_statistics(result)

    assert statistics == {
        "repository_name": tmp_path.name,
        "total_files": 1,
        "total_directories": 1,
        "total_symlinks": 0,
    }


def test_invalid_repository_rejected():
    service = FileDiscoveryService()

    with pytest.raises(RepositoryScanError) as error:
        service.discover("invalid")

    assert error.value.code == "INVALID_REPOSITORY"


def test_invalid_statistics_result_rejected():
    with pytest.raises(ValueError):
        FileDiscoveryService.get_statistics("invalid")
