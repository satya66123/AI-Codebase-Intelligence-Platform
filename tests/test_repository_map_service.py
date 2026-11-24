
import pytest

from app.application.repository_input import RepositoryInfo
from app.application.repository_scanner import RepositoryScanner
from app.application.repository_map_service import (
    RepositoryMapService,
    RepositoryMapError,
)


def scan_repository(root):
    repository = RepositoryInfo(
        root=root,
        name=root.name,
        is_git_repository=False
    )

    return RepositoryScanner().scan(repository)


def test_build_map_with_files_and_directories(tmp_path):
    source = tmp_path / "src"
    source.mkdir()

    (tmp_path / "README.md").write_text("# Project")
    (source / "main.py").write_text("print('hello')")

    result = scan_repository(tmp_path)

    service = RepositoryMapService()
    tree = service.build_map(result)

    assert tmp_path.name in tree
    assert "src" in tree
    assert "README.md" in tree
    assert "main.py" in tree


def test_build_map_with_nested_directories(tmp_path):
    nested = tmp_path / "src" / "services"
    nested.mkdir(parents=True)

    (nested / "user.py").write_text("class User: pass")

    result = scan_repository(tmp_path)

    tree = RepositoryMapService().build_map(result)

    assert "src" in tree
    assert "services" in tree
    assert "user.py" in tree


def test_build_map_with_empty_directory(tmp_path):
    (tmp_path / "empty").mkdir()

    result = scan_repository(tmp_path)

    tree = RepositoryMapService().build_map(result)

    assert "empty" in tree


def test_build_map_without_files(tmp_path):
    (tmp_path / "main.py").write_text("print('hello')")
    (tmp_path / "src").mkdir()

    result = scan_repository(tmp_path)

    tree = RepositoryMapService().build_map(
        result,
        include_files=False
    )

    assert "src" in tree
    assert "main.py" not in tree


def test_build_map_for_empty_repository(tmp_path):
    result = scan_repository(tmp_path)

    tree = RepositoryMapService().build_map(result)

    assert tree == tmp_path.name


def test_invalid_scan_result_rejected():
    service = RepositoryMapService()

    with pytest.raises(RepositoryMapError):
        service.build_map("invalid")


def test_outside_repository_entry_rejected(tmp_path):
    outside_file = tmp_path.parent / "outside.py"

    from app.application.repository_scanner import (
        RepositoryScanResult,
    )

    result = RepositoryScanResult(
        root=tmp_path,
        files=(outside_file,),
        directories=(),
        symlinks=()
    )

    service = RepositoryMapService()

    with pytest.raises(RepositoryMapError):
        service.build_map(result)
