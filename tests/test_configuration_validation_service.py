
import json
from pathlib import Path

import pytest

from appy.application.configuration_validation_service import (
    ConfigurationIssue,
    ConfigurationIssueSeverity,
    ConfigurationValidationError,
    ConfigurationValidationResult,
    ConfigurationValidationService,
)


@pytest.fixture
def repository(tmp_path):
    return tmp_path


@pytest.fixture
def service():
    return ConfigurationValidationService()


def write_file(root: Path, name: str, content: str) -> Path:
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def test_valid_json_configuration(repository, service):
    write_file(repository, "settings.json", '{"application": {"name": "Demo"}}')

    result = service.validate(repository, config_files=["settings.json"])

    assert result.is_valid is True
    assert result.files_checked == 1
    assert result.error_count == 0


def test_invalid_json_syntax_is_reported(repository, service):
    write_file(repository, "settings.json", '{"application": ')

    result = service.validate(repository, config_files=["settings.json"])

    assert result.is_valid is False
    assert result.error_count == 1
    assert result.issues[0].code == "INVALID_CONFIG_SYNTAX"


def test_valid_toml_configuration(repository, service):
    write_file(
        repository,
        "pyproject.toml",
        '[project]\nname = "demo"\nversion = "1.0.0"\n',
    )

    result = service.validate(repository, config_files=["pyproject.toml"])

    assert result.is_valid is True
    assert result.files_checked == 1


def test_invalid_toml_syntax_is_reported(repository, service):
    write_file(repository, "pyproject.toml", 'name = "demo"\ninvalid = [\n')

    result = service.validate(repository, config_files=["pyproject.toml"])

    assert result.is_valid is False
    assert result.issues[0].code == "INVALID_CONFIG_SYNTAX"


def test_valid_ini_configuration(repository, service):
    write_file(
        repository,
        "settings.ini",
        "[application]\nname = Demo\n",
    )

    result = service.validate(repository, config_files=["settings.ini"])

    assert result.is_valid is True


def test_invalid_ini_syntax_is_reported(repository, service):
    write_file(repository, "settings.ini", "this is not an ini section\n")

    result = service.validate(repository, config_files=["settings.ini"])

    assert result.is_valid is False
    assert result.issues[0].code == "INVALID_CONFIG_SYNTAX"


def test_valid_env_configuration(repository, service):
    write_file(
        repository,
        ".env",
        "# Application settings\nAPP_NAME=Demo\nDEBUG=true\nexport PORT=8000\n",
    )

    result = service.validate(repository, config_files=[".env"])

    assert result.is_valid is True
    assert result.files_checked == 1


def test_invalid_env_assignment_is_reported(repository, service):
    write_file(repository, ".env", "APP_NAME\n")

    result = service.validate(repository, config_files=[".env"])

    assert result.is_valid is False
    assert result.issues[0].code == "INVALID_CONFIG_SYNTAX"


def test_invalid_env_variable_name_is_reported(repository, service):
    write_file(repository, ".env", "1INVALID=value\n")

    result = service.validate(repository, config_files=[".env"])

    assert result.is_valid is False
    assert result.issues[0].code == "INVALID_CONFIG_SYNTAX"


def test_duplicate_env_variable_is_reported(repository, service):
    write_file(repository, ".env", "APP_NAME=Demo\nAPP_NAME=Other\n")

    result = service.validate(repository, config_files=[".env"])

    assert result.is_valid is False
    assert result.issues[0].code == "INVALID_CONFIG_SYNTAX"


def test_required_file_missing_is_reported(repository, service):
    result = service.validate(
        repository,
        config_files=[],
        required_files=["pyproject.toml"],
    )

    assert result.is_valid is False
    assert any(
        issue.code == "REQUIRED_CONFIG_MISSING"
        for issue in result.issues
    )


def test_required_file_present(repository, service):
    write_file(repository, "pyproject.toml", '[project]\nname = "demo"\n')

    result = service.validate(
        repository,
        config_files=[],
        required_files=["pyproject.toml"],
    )

    assert result.is_valid is True


def test_required_json_key_present(repository, service):
    write_file(
        repository,
        "settings.json",
        json.dumps({"application": {"name": "Demo"}}),
    )

    result = service.validate(
        repository,
        config_files=["settings.json"],
        required_keys={"settings.json": ["application.name"]},
    )

    assert result.is_valid is True


def test_required_json_key_missing(repository, service):
    write_file(
        repository,
        "settings.json",
        json.dumps({"application": {}}),
    )

    result = service.validate(
        repository,
        config_files=["settings.json"],
        required_keys={"settings.json": ["application.name"]},
    )

    assert result.is_valid is False
    assert any(
        issue.code == "REQUIRED_CONFIG_KEY_MISSING"
        for issue in result.issues
    )


def test_multiple_required_keys(repository, service):
    write_file(
        repository,
        "settings.json",
        json.dumps({"application": {"name": "Demo", "version": "1"}}),
    )

    result = service.validate(
        repository,
        config_files=["settings.json"],
        required_keys={
            "settings.json": ["application.name", "application.version"]
        },
    )

    assert result.is_valid is True


def test_missing_selected_file_is_reported(repository, service):
    result = service.validate(
        repository,
        config_files=["missing.json"],
    )

    assert result.is_valid is False
    assert any(
        issue.code == "CONFIG_FILE_MISSING"
        for issue in result.issues
    )


def test_duplicate_config_file_is_reported(repository, service):
    write_file(repository, "settings.json", "{}")

    result = service.validate(
        repository,
        config_files=["settings.json", "settings.json"],
    )

    assert result.is_valid is False
    assert any(
        issue.code == "DUPLICATE_CONFIG_FILE"
        for issue in result.issues
    )


@pytest.mark.parametrize(
    "invalid_path",
    [
        "../outside.json",
        "/absolute/config.json",
        "folder/../config.json",
        "./config.json",
        "folder//config.json",
        "C:\\outside\\config.json",
    ],
)
def test_invalid_relative_paths_are_rejected(
    repository, service, invalid_path
):
    with pytest.raises(ConfigurationValidationError):
        service.validate(repository, config_files=[invalid_path])


def test_nonexistent_repository_is_rejected(service, tmp_path):
    with pytest.raises(ConfigurationValidationError):
        service.validate(tmp_path / "missing")


def test_file_as_repository_root_is_rejected(service, tmp_path):
    file_path = write_file(tmp_path, "file.txt", "content")

    with pytest.raises(ConfigurationValidationError):
        service.validate(file_path)


def test_invalid_max_file_size_is_rejected():
    with pytest.raises(ConfigurationValidationError):
        ConfigurationValidationService(max_file_size_bytes=0)


def test_boolean_max_file_size_is_rejected():
    with pytest.raises(ConfigurationValidationError):
        ConfigurationValidationService(max_file_size_bytes=True)


def test_large_configuration_file_is_reported(repository):
    write_file(repository, "settings.json", '{"value": "this is too large"}')
    service = ConfigurationValidationService(max_file_size_bytes=5)

    result = service.validate(repository, config_files=["settings.json"])

    assert result.is_valid is False
    assert result.issues[0].code == "CONFIG_FILE_TOO_LARGE"
    assert result.files_checked == 0


def test_invalid_utf8_file_is_reported(repository, service):
    path = repository / "settings.json"
    path.write_bytes(b"\xff\xfe\xfa")

    result = service.validate(repository, config_files=["settings.json"])

    assert result.is_valid is False
    assert result.issues[0].code == "CONFIG_FILE_UNREADABLE"


def test_directory_selected_as_config_file_is_reported(repository, service):
    (repository / "settings.json").mkdir()

    result = service.validate(repository, config_files=["settings.json"])

    assert result.is_valid is False
    assert any(
        issue.code == "CONFIG_NOT_A_FILE"
        for issue in result.issues
    )


def test_unsupported_format_generates_warning(repository, service):
    write_file(repository, "settings.xyz", "some content")

    result = service.validate(repository, config_files=["settings.xyz"])

    assert result.is_valid is True
    assert result.warning_count == 1
    assert result.issues[0].code == "UNSUPPORTED_CONFIG_FORMAT"


def test_auto_discovery_finds_common_configuration_files(repository, service):
    write_file(repository, "pyproject.toml", '[project]\nname = "demo"\n')
    write_file(repository, "settings.json", '{"enabled": true}')
    write_file(repository, "src/module.py", "print('hello')")

    result = service.validate(repository)

    assert result.is_valid is True
    assert result.files_checked == 2


def test_auto_discovery_ignores_virtual_environment(repository, service):
    write_file(repository, ".venv/config.json", "{ invalid json")
    write_file(repository, "settings.json", "{}")

    result = service.validate(repository)

    assert result.is_valid is True
    assert result.files_checked == 1


def test_auto_discovery_ignores_git_directory(repository, service):
    write_file(repository, ".git/config.json", "{ invalid json")
    write_file(repository, "settings.json", "{}")

    result = service.validate(repository)

    assert result.is_valid is True
    assert result.files_checked == 1


def test_nested_configuration_file_is_discovered(repository, service):
    write_file(repository, "config/application.json", '{"enabled": true}')

    result = service.validate(repository)

    assert result.is_valid is True
    assert result.files_checked == 1


def test_required_keys_for_invalid_file_do_not_crash(repository, service):
    write_file(repository, "settings.json", "{invalid")

    result = service.validate(
        repository,
        config_files=["settings.json"],
        required_keys={"settings.json": ["application.name"]},
    )

    assert result.is_valid is False
    assert any(
        issue.code == "INVALID_CONFIG_SYNTAX"
        for issue in result.issues
    )


def test_required_keys_must_be_mapping(repository, service):
    with pytest.raises(ConfigurationValidationError):
        service.validate(
            repository,
            config_files=[],
            required_keys=["application.name"],
        )


def test_required_files_must_be_collection(repository, service):
    with pytest.raises(ConfigurationValidationError):
        service.validate(
            repository,
            config_files=[],
            required_files="pyproject.toml",
        )


def test_empty_required_file_name_is_rejected(repository, service):
    with pytest.raises(ConfigurationValidationError):
        service.validate(
            repository,
            config_files=[],
            required_files=[""],
        )


def test_issue_model_validates_code():
    with pytest.raises(ValueError):
        ConfigurationIssue(code="", message="Invalid")


def test_issue_model_validates_message():
    with pytest.raises(ValueError):
        ConfigurationIssue(code="INVALID", message="")


def test_issue_model_validates_severity():
    with pytest.raises(TypeError):
        ConfigurationIssue(
            code="INVALID",
            message="Invalid",
            severity="error",
        )


def test_result_counts_errors_and_warnings(repository):
    issues = (
        ConfigurationIssue(
            code="ERROR",
            message="An error",
            severity=ConfigurationIssueSeverity.ERROR,
        ),
        ConfigurationIssue(
            code="WARNING",
            message="A warning",
            severity=ConfigurationIssueSeverity.WARNING,
        ),
    )

    result = ConfigurationValidationResult(
        repository_root=repository,
        is_valid=False,
        files_checked=2,
        issues=issues,
    )

    assert result.error_count == 1
    assert result.warning_count == 1
    assert result.healthy is False


def test_healthy_result(repository):
    result = ConfigurationValidationResult(
        repository_root=repository,
        is_valid=True,
        files_checked=1,
        issues=(),
    )

    assert result.healthy is True
    assert result.error_count == 0
    assert result.warning_count == 0


def test_result_rejects_negative_files_checked(repository):
    with pytest.raises(ValueError):
        ConfigurationValidationResult(
            repository_root=repository,
            is_valid=True,
            files_checked=-1,
            issues=(),
        )


def test_result_rejects_non_tuple_issues(repository):
    with pytest.raises(TypeError):
        ConfigurationValidationResult(
            repository_root=repository,
            is_valid=True,
            files_checked=0,
            issues=[],
        )


def test_empty_configuration_selection_is_valid(repository, service):
    result = service.validate(repository, config_files=[])

    assert result.is_valid is True
    assert result.files_checked == 0
    assert result.issues == ()


def test_yaml_validation_when_pyyaml_is_available(repository, service):
    pytest.importorskip("yaml")
    write_file(repository, "settings.yaml", "application:\n  name: Demo\n")

    result = service.validate(repository, config_files=["settings.yaml"])

    assert result.is_valid is True
    assert result.files_checked == 1


def test_invalid_yaml_is_reported_when_pyyaml_is_available(
    repository, service
):
    pytest.importorskip("yaml")
    write_file(repository, "settings.yaml", "application: [invalid")

    result = service.validate(repository, config_files=["settings.yaml"])

    assert result.is_valid is False
    assert result.issues[0].code == "INVALID_CONFIG_SYNTAX"
