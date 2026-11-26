
import pytest

from appy.application.repository_input import RepositoryInfo
from appy.application.repository_scanner import RepositoryScanner
from appy.application.ignore_rule_service import (
    IgnoreRuleService,
    IgnoreRuleError,
)


def scan_repository(root):
    repository = RepositoryInfo(
        root=root,
        name=root.name,
        is_git_repository=False
    )
    return RepositoryScanner().scan(repository)


def test_default_ignored_directories(tmp_path):
    venv = tmp_path / ".venv"
    venv.mkdir()
    (venv / "package.py").write_text("print('ignored')")

    (tmp_path / "main.py").write_text("print('included')")

    result = scan_repository(tmp_path)
    filtered = IgnoreRuleService().filter_scan_result(result)

    assert {path.name for path in filtered.files} == {"main.py"}
    assert filtered.total_directories == 0


def test_default_ignored_file_patterns(tmp_path):
    (tmp_path / "main.py").write_text("print('hello')")
    (tmp_path / "cache.pyc").write_text("compiled")

    result = scan_repository(tmp_path)
    filtered = IgnoreRuleService().filter_scan_result(result)

    assert {path.name for path in filtered.files} == {"main.py"}


def test_custom_ignored_directory(tmp_path):
    generated = tmp_path / "generated"
    generated.mkdir()
    (generated / "output.py").write_text("print('generated')")

    (tmp_path / "main.py").write_text("print('main')")

    result = scan_repository(tmp_path)

    filtered = IgnoreRuleService().filter_scan_result(
        result,
        ignored_directories=["generated"]
    )

    assert {path.name for path in filtered.files} == {"main.py"}
    assert filtered.total_directories == 0


def test_custom_ignored_file_pattern(tmp_path):
    (tmp_path / "main.py").write_text("print('main')")
    (tmp_path / "secret.env").write_text("KEY=value")

    result = scan_repository(tmp_path)

    filtered = IgnoreRuleService().filter_scan_result(
        result,
        ignored_files=["*.env"]
    )

    assert {path.name for path in filtered.files} == {"main.py"}


def test_gitignore_file_pattern(tmp_path):
    (tmp_path / ".gitignore").write_text(
        "*.log\n",
        encoding="utf-8"
    )
    (tmp_path / "appy.py").write_text("print('hello')")
    (tmp_path / "debug.log").write_text("debug")

    result = scan_repository(tmp_path)
    filtered = IgnoreRuleService().filter_scan_result(result)

    assert "appy.py" in {path.name for path in filtered.files}
    assert "debug.log" not in {path.name for path in filtered.files}



def test_gitignore_directory_pattern(tmp_path):
    (tmp_path / ".gitignore").write_text(
        "logs/\n",
        encoding="utf-8"
    )

    logs = tmp_path / "logs"
    logs.mkdir()
    (logs / "appy.log").write_text("debug")

    (tmp_path / "main.py").write_text("print('hello')")

    result = scan_repository(tmp_path)
    filtered = IgnoreRuleService().filter_scan_result(result)

    discovered_files = {path.name for path in filtered.files}

    assert discovered_files == {"main.py", ".gitignore"}
    assert "appy.log" not in discovered_files
    assert filtered.total_directories == 0



def test_gitignore_can_be_disabled(tmp_path):
    (tmp_path / ".gitignore").write_text(
        "*.log\n",
        encoding="utf-8"
    )
    (tmp_path / "debug.log").write_text("debug")

    result = scan_repository(tmp_path)

    filtered = IgnoreRuleService().filter_scan_result(
        result,
        respect_gitignore=False
    )

    assert "debug.log" in {path.name for path in filtered.files}


def test_original_scan_result_is_unchanged(tmp_path):
    (tmp_path / "main.py").write_text("print('hello')")
    (tmp_path / "cache.pyc").write_text("compiled")

    result = scan_repository(tmp_path)
    original_count = result.total_files

    IgnoreRuleService().filter_scan_result(result)

    assert result.total_files == original_count


def test_invalid_scan_result_rejected():
    with pytest.raises(IgnoreRuleError):
        IgnoreRuleService().filter_scan_result("invalid")


def test_invalid_ignore_pattern_rejected(tmp_path):
    (tmp_path / "main.py").write_text("print('hello')")

    result = scan_repository(tmp_path)

    with pytest.raises(IgnoreRuleError):
        IgnoreRuleService().filter_scan_result(
            result,
            ignored_files=[""]
        )
