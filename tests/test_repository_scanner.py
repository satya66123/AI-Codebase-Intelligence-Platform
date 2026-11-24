import pytest

from app.application.repository_input import (
    RepositoryInfo,
)
from app.application.repository_scanner import (
    RepositoryScanner,
    RepositoryScanError,
)


def create_repository(root):
    return RepositoryInfo(
        root=root,
        name=root.name,
        is_git_repository=False
    )


def test_scan_repository_files(tmp_path):
    (tmp_path / "main.py").write_text("print('hello')")
    (tmp_path / "README.md").write_text("# Project")

    scanner = RepositoryScanner()
    result = scanner.scan(create_repository(tmp_path))

    discovered_names = {path.name for path in result.files}

    assert discovered_names == {"main.py", "README.md"}
    assert result.total_files == 2


def test_scan_nested_directories(tmp_path):
    source = tmp_path / "src"
    services = source / "services"

    services.mkdir(parents=True)

    (source / "main.py").write_text("print('main')")
    (services / "user.py").write_text("class UserService: pass")

    scanner = RepositoryScanner()
    result = scanner.scan(create_repository(tmp_path))

    directory_names = {path.name for path in result.directories}
    file_names = {path.name for path in result.files}

    assert directory_names == {"src", "services"}
    assert file_names == {"main.py", "user.py"}
    assert result.total_directories == 2
    assert result.total_files == 2


def test_scan_empty_repository(tmp_path):
    scanner = RepositoryScanner()

    result = scanner.scan(create_repository(tmp_path))

    assert result.files == ()
    assert result.directories == ()
    assert result.symlinks == ()
    assert result.total_files == 0


def test_scan_returns_absolute_paths(tmp_path):
    (tmp_path / "main.py").write_text("print('hello')")

    scanner = RepositoryScanner()
    result = scanner.scan(create_repository(tmp_path))

    assert result.root.is_absolute()

    for path in result.files:
        assert path.is_absolute()


def test_invalid_repository_info_rejected():
    scanner = RepositoryScanner()

    with pytest.raises(RepositoryScanError) as error:
        scanner.scan("invalid")

    assert error.value.code == "INVALID_REPOSITORY"


