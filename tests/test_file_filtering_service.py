
import pytest

from appy.application.repository_input import RepositoryInfo
from appy.application.repository_scanner import RepositoryScanner
from appy.application.file_filtering_service import (
    FileFilteringService,
)


def scan_repository(root):
    repository = RepositoryInfo(
        root=root,
        name=root.name,
        is_git_repository=False,
    )
    return RepositoryScanner().scan(repository)


def test_filter_files_using_default_rules(tmp_path):
    (tmp_path / "main.py").write_text("print('hello')")
    (tmp_path / "cache.pyc").write_text("compiled")

    original = scan_repository(tmp_path)

    filtered = FileFilteringService().filter_files(original)

    assert {path.name for path in filtered.files} == {
        "main.py",
        ".gitignore",
    } if (tmp_path / ".gitignore").exists() else {
        "main.py"
    }


def test_filter_files_using_custom_rules(tmp_path):
    (tmp_path / "main.py").write_text("print('hello')")
    (tmp_path / "secret.env").write_text("KEY=value")

    original = scan_repository(tmp_path)

    filtered = FileFilteringService().filter_files(
        original,
        ignored_files=["*.env"],
    )

    assert {path.name for path in filtered.files} == {"main.py"}


def test_filter_files_using_gitignore(tmp_path):
    (tmp_path / ".gitignore").write_text(
        "*.log\n",
        encoding="utf-8",
    )
    (tmp_path / "main.py").write_text("print('hello')")
    (tmp_path / "debug.log").write_text("debug")

    original = scan_repository(tmp_path)

    filtered = FileFilteringService().filter_files(original)

    assert "debug.log" not in {
        path.name for path in filtered.files
    }
    assert "main.py" in {
        path.name for path in filtered.files
    }


def test_filtering_statistics(tmp_path):
    (tmp_path / "main.py").write_text("print('hello')")
    (tmp_path / "cache.pyc").write_text("compiled")

    original = scan_repository(tmp_path)

    filtered = FileFilteringService().filter_files(original)

    statistics = FileFilteringService.get_filter_statistics(
        original,
        filtered,
    )

    assert statistics["original_files"] == 2
    assert statistics["filtered_files"] == 1
    assert statistics["ignored_files"] == 1


def test_original_result_remains_unchanged(tmp_path):
    (tmp_path / "main.py").write_text("print('hello')")
    (tmp_path / "cache.pyc").write_text("compiled")

    original = scan_repository(tmp_path)
    original_count = original.total_files

    FileFilteringService().filter_files(original)

    assert original.total_files == original_count


def test_invalid_scan_result_rejected():
    with pytest.raises(Exception):
        FileFilteringService().filter_files("invalid")


def test_invalid_statistics_rejected():
    with pytest.raises(ValueError):
        FileFilteringService.get_filter_statistics(
            "invalid",
            "invalid",
        )
