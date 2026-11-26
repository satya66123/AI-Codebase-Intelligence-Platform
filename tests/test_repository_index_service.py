
import pytest

from appy.application.repository_input import RepositoryInfo
from appy.application.repository_scanner import RepositoryScanner
from appy.application.metadata_extraction_service import (
    MetadataExtractionService,
)
from appy.application.repository_index_service import (
    RepositoryIndexService,
    RepositoryIndexError,
)


def create_repository_index(root):
    repository = RepositoryInfo(
        root=root,
        name=root.name,
        is_git_repository=False,
    )

    scan_result = RepositoryScanner().scan(repository)

    metadata = MetadataExtractionService().extract_repository_metadata(
        scan_result
    )

    return RepositoryIndexService().build_index(metadata)


def test_build_repository_index(tmp_path):
    (tmp_path / "main.py").write_text("print('hello')")
    (tmp_path / "appy.js").write_text("console.log('hello')")

    index = create_repository_index(tmp_path)

    assert index["repository_name"] == tmp_path.name
    assert index["total_files"] == 2
    assert len(index["files"]) == 2


def test_search_files_by_name(tmp_path):
    (tmp_path / "main.py").write_text("print('hello')")
    (tmp_path / "appy.js").write_text("console.log('hello')")

    index = create_repository_index(tmp_path)

    results = RepositoryIndexService().search_files(
        index,
        "main",
    )

    assert len(results) == 1
    assert results[0]["name"] == "main.py"


def test_search_files_by_extension(tmp_path):
    (tmp_path / "main.py").write_text("print('hello')")
    (tmp_path / "appy.js").write_text("console.log('hello')")

    index = create_repository_index(tmp_path)

    results = RepositoryIndexService().search_files(
        index,
        ".py",
    )

    assert len(results) == 1
    assert results[0]["extension"] == ".py"


def test_search_files_by_language(tmp_path):
    (tmp_path / "main.py").write_text("print('hello')")
    (tmp_path / "service.py").write_text("print('service')")
    (tmp_path / "appy.js").write_text("console.log('hello')")

    index = create_repository_index(tmp_path)

    results = RepositoryIndexService().search_files(
        index,
        "python",
    )

    assert len(results) == 2
    assert all(item["language"] == "Python" for item in results)


def test_search_files_case_insensitive(tmp_path):
    (tmp_path / "Main.py").write_text("print('hello')")

    index = create_repository_index(tmp_path)

    results = RepositoryIndexService().search_files(
        index,
        "MAIN",
    )

    assert len(results) == 1


def test_get_file_by_relative_path(tmp_path):
    source = tmp_path / "src"
    source.mkdir()

    (source / "main.py").write_text("print('hello')")

    index = create_repository_index(tmp_path)

    result = RepositoryIndexService().get_file(
        index,
        "src/main.py",
    )

    assert result is not None
    assert result["name"] == "main.py"


def test_get_missing_file_returns_none(tmp_path):
    (tmp_path / "main.py").write_text("print('hello')")

    index = create_repository_index(tmp_path)

    result = RepositoryIndexService().get_file(
        index,
        "missing.py",
    )

    assert result is None


def test_get_language_files(tmp_path):
    (tmp_path / "main.py").write_text("print('hello')")
    (tmp_path / "service.py").write_text("print('service')")
    (tmp_path / "appy.js").write_text("console.log('hello')")

    index = create_repository_index(tmp_path)

    results = RepositoryIndexService().get_language_files(
        index,
        "Python",
    )

    assert len(results) == 2


def test_empty_repository_index(tmp_path):
    index = create_repository_index(tmp_path)

    assert index["total_files"] == 0
    assert index["files"] == []
    assert index["languages"] == {}


def test_invalid_index_rejected():
    service = RepositoryIndexService()

    with pytest.raises(RepositoryIndexError):
        service.search_files("invalid", "main")


def test_empty_search_query_rejected(tmp_path):
    (tmp_path / "main.py").write_text("print('hello')")

    index = create_repository_index(tmp_path)

    with pytest.raises(RepositoryIndexError):
        RepositoryIndexService().search_files(index, "")


def test_invalid_metadata_rejected():
    with pytest.raises(RepositoryIndexError):
        RepositoryIndexService().build_index("invalid")
