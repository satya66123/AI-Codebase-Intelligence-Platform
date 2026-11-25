
"""Validate configuration files in a repository."""

from __future__ import annotations

import configparser
import importlib.util
import json
import os
import re
import tomllib
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Mapping


class ConfigurationValidationError(ValueError):
    """Raised when configuration validation cannot be performed."""


class ConfigurationIssueSeverity(str, Enum):
    ERROR = "error"
    WARNING = "warning"


@dataclass(frozen=True)
class ConfigurationIssue:
    code: str
    message: str
    path: str = ""
    severity: ConfigurationIssueSeverity = ConfigurationIssueSeverity.ERROR

    def __post_init__(self) -> None:
        if not isinstance(self.code, str) or not self.code.strip():
            raise ValueError("Issue code must be a non-empty string.")
        if not isinstance(self.message, str) or not self.message.strip():
            raise ValueError("Issue message must be a non-empty string.")
        if not isinstance(self.path, str):
            raise TypeError("Issue path must be a string.")
        if not isinstance(self.severity, ConfigurationIssueSeverity):
            raise TypeError("Issue severity must be a ConfigurationIssueSeverity.")


@dataclass(frozen=True)
class ConfigurationValidationResult:
    repository_root: Path
    is_valid: bool
    files_checked: int
    issues: tuple[ConfigurationIssue, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.repository_root, Path):
            raise TypeError("repository_root must be a Path.")
        if not isinstance(self.is_valid, bool):
            raise TypeError("is_valid must be a boolean.")
        if isinstance(self.files_checked, bool) or not isinstance(self.files_checked, int):
            raise TypeError("files_checked must be an integer.")
        if self.files_checked < 0:
            raise ValueError("files_checked cannot be negative.")
        if not isinstance(self.issues, tuple):
            raise TypeError("issues must be a tuple.")
        if not all(isinstance(issue, ConfigurationIssue) for issue in self.issues):
            raise TypeError("issues must contain ConfigurationIssue objects.")

    @property
    def error_count(self) -> int:
        return sum(
            issue.severity == ConfigurationIssueSeverity.ERROR
            for issue in self.issues
        )

    @property
    def warning_count(self) -> int:
        return sum(
            issue.severity == ConfigurationIssueSeverity.WARNING
            for issue in self.issues
        )

    @property
    def healthy(self) -> bool:
        return self.is_valid and self.error_count == 0


class ConfigurationValidationService:
    """Discover and validate common repository configuration files."""

    SUPPORTED_EXTENSIONS = {
        ".json",
        ".toml",
        ".ini",
        ".cfg",
        ".conf",
        ".env",
        ".yaml",
        ".yml",
    }

    DEFAULT_CONFIG_NAMES = (
        "pyproject.toml",
        "setup.cfg",
        "tox.ini",
        "pytest.ini",
        ".flake8",
        "mypy.ini",
        ".coveragerc",
        "config.json",
        "settings.json",
        "config.toml",
        "config.yaml",
        "config.yml",
        ".env",
    )

    EXCLUDED_DIRECTORY_NAMES = {
        ".git",
        ".venv",
        "venv",
        "__pycache__",
        "node_modules",
        ".pytest_cache",
        ".mypy_cache",
        ".tox",
        "build",
        "dist",
    }

    def __init__(self, max_file_size_bytes: int = 1_048_576) -> None:
        if (
            isinstance(max_file_size_bytes, bool)
            or not isinstance(max_file_size_bytes, int)
            or max_file_size_bytes <= 0
        ):
            raise ConfigurationValidationError(
                "max_file_size_bytes must be a positive integer."
            )

        self.max_file_size_bytes = max_file_size_bytes

    def validate(
        self,
        repository_root: str | os.PathLike[str],
        config_files: tuple[str | os.PathLike[str], ...] | list[str | os.PathLike[str]] | None = None,
        required_files: tuple[str, ...] | list[str] = (),
        required_keys: Mapping[str, tuple[str, ...] | list[str]] | None = None,
    ) -> ConfigurationValidationResult:
        """Validate selected or automatically discovered configuration files.

        required_keys maps a repository-relative configuration path to required
        dotted keys. For example:
            {"settings.json": ("database.host", "application.name")}
        """
        root = self._validate_root(repository_root)
        required_files = self._validate_string_collection(
            required_files, "required_files"
        )

        if required_keys is None:
            required_keys = {}
        if not isinstance(required_keys, Mapping):
            raise ConfigurationValidationError("required_keys must be a mapping.")

        normalized_required_keys: dict[str, tuple[str, ...]] = {}
        for file_name, keys in required_keys.items():
            normalized_name = self._normalize_relative_path(file_name)
            normalized_required_keys[normalized_name] = self._validate_string_collection(
                keys, f"required keys for {normalized_name}"
            )

        selected_files = (
            self._discover_configuration_files(root)
            if config_files is None
            else self._validate_string_collection(config_files, "config_files")
        )

        normalized_files: list[str] = []
        seen: set[str] = set()
        issues: list[ConfigurationIssue] = []

        for item in selected_files:
            relative = self._normalize_relative_path(item)
            if relative in seen:
                issues.append(
                    ConfigurationIssue(
                        code="DUPLICATE_CONFIG_FILE",
                        message="Configuration file was specified more than once.",
                        path=relative,
                    )
                )
                continue
            seen.add(relative)
            normalized_files.append(relative)

        for required in required_files:
            normalized = self._normalize_relative_path(required)
            if normalized not in seen:
                normalized_files.append(normalized)
                seen.add(normalized)

        for required in required_files:
            normalized = self._normalize_relative_path(required)
            if not (root / normalized).exists():
                issues.append(
                    ConfigurationIssue(
                        code="REQUIRED_CONFIG_MISSING",
                        message="Required configuration file does not exist.",
                        path=normalized,
                    )
                )

        files_checked = 0
        parsed_data: dict[str, Any] = {}

        for relative in normalized_files:
            file_path = root / relative

            if not self._is_contained(root, file_path):
                issues.append(
                    ConfigurationIssue(
                        code="PATH_OUTSIDE_REPOSITORY",
                        message="Configuration path resolves outside the repository.",
                        path=relative,
                    )
                )
                continue

            if not file_path.exists():
                if relative not in {
                    self._normalize_relative_path(name) for name in required_files
                }:
                    issues.append(
                        ConfigurationIssue(
                            code="CONFIG_FILE_MISSING",
                            message="Configuration file does not exist.",
                            path=relative,
                        )
                    )
                continue

            if file_path.is_symlink():
                issues.append(
                    ConfigurationIssue(
                        code="CONFIG_SYMLINK_NOT_ALLOWED",
                        message="Configuration files must not be symbolic links.",
                        path=relative,
                    )
                )
                continue

            if not file_path.is_file():
                issues.append(
                    ConfigurationIssue(
                        code="CONFIG_NOT_A_FILE",
                        message="Configuration path is not a regular file.",
                        path=relative,
                    )
                )
                continue

            try:
                file_size = file_path.stat().st_size
            except OSError:
                issues.append(
                    ConfigurationIssue(
                        code="CONFIG_FILE_UNREADABLE",
                        message="Unable to read configuration file metadata.",
                        path=relative,
                    )
                )
                continue

            if file_size > self.max_file_size_bytes:
                issues.append(
                    ConfigurationIssue(
                        code="CONFIG_FILE_TOO_LARGE",
                        message=(
                            f"Configuration file exceeds the maximum size of "
                            f"{self.max_file_size_bytes} bytes."
                        ),
                        path=relative,
                    )
                )
                continue

            try:
                content = file_path.read_text(encoding="utf-8")
            except (OSError, UnicodeError):
                issues.append(
                    ConfigurationIssue(
                        code="CONFIG_FILE_UNREADABLE",
                        message="Configuration file cannot be read as UTF-8 text.",
                        path=relative,
                    )
                )
                continue

            files_checked += 1
            parsed, data, parse_issue = self._parse_configuration(
                relative, content
            )

            if parse_issue is not None:
                issues.append(parse_issue)
            elif parsed:
                parsed_data[relative] = data

        for relative, keys in normalized_required_keys.items():
            if relative not in parsed_data:
                continue
            data = parsed_data[relative]
            for key in keys:
                if not self._has_dotted_key(data, key):
                    issues.append(
                        ConfigurationIssue(
                            code="REQUIRED_CONFIG_KEY_MISSING",
                            message=f"Required configuration key '{key}' is missing.",
                            path=relative,
                        )
                    )

        is_valid = not any(
            issue.severity == ConfigurationIssueSeverity.ERROR
            for issue in issues
        )

        return ConfigurationValidationResult(
            repository_root=root,
            is_valid=is_valid,
            files_checked=files_checked,
            issues=tuple(issues),
        )

    @staticmethod
    def _validate_root(value: str | os.PathLike[str]) -> Path:
        try:
            root = Path(value).resolve(strict=True)
        except (TypeError, ValueError, OSError) as exc:
            raise ConfigurationValidationError(
                "A valid existing repository directory is required."
            ) from exc

        if not root.is_dir():
            raise ConfigurationValidationError(
                "Repository root must be a directory."
            )
        return root

    @staticmethod
    def _validate_string_collection(
        values: Any, field_name: str
    ) -> tuple[str, ...]:
        if isinstance(values, (str, bytes)) or not isinstance(values, (tuple, list)):
            raise ConfigurationValidationError(
                f"{field_name} must be a tuple or list of strings."
            )
        if not all(isinstance(value, str) and value.strip() for value in values):
            raise ConfigurationValidationError(
                f"{field_name} must contain only non-empty strings."
            )
        return tuple(values)

    @staticmethod
    def _normalize_relative_path(value: str | os.PathLike[str]) -> str:
        if not isinstance(value, (str, os.PathLike)):
            raise ConfigurationValidationError(
                "Configuration paths must be strings or path-like values."
            )

        raw = os.fspath(value)
        if not isinstance(raw, str) or not raw.strip():
            raise ConfigurationValidationError(
                "Configuration paths must be non-empty strings."
            )

        normalized = raw.replace("\\", "/")
        parts = normalized.split("/")

        if (
            normalized.startswith("/")
            or re.match(r"^[A-Za-z]:", normalized)
            or any(part in ("", ".", "..") for part in parts)
        ):
            raise ConfigurationValidationError(
                f"Configuration path must be a normalized relative path: {raw}"
            )

        return normalized

    def _discover_configuration_files(self, root: Path) -> tuple[str, ...]:
        found: set[str] = set()

        for name in self.DEFAULT_CONFIG_NAMES:
            candidate = root / name
            if candidate.is_file() and not candidate.is_symlink():
                found.add(candidate.relative_to(root).as_posix())

        for current_root, directories, files in os.walk(root, followlinks=False):
            directories[:] = [
                directory
                for directory in directories
                if directory not in self.EXCLUDED_DIRECTORY_NAMES
                and not (Path(current_root) / directory).is_symlink()
            ]

            current_path = Path(current_root)
            for filename in files:
                candidate = current_path / filename
                if candidate.is_symlink():
                    continue
                if candidate.suffix.lower() in self.SUPPORTED_EXTENSIONS:
                    found.add(candidate.relative_to(root).as_posix())

        return tuple(sorted(found))

    @staticmethod
    def _is_contained(root: Path, candidate: Path) -> bool:
        try:
            candidate.resolve(strict=False).relative_to(root)
            return True
        except (ValueError, OSError):
            return False

    def _parse_configuration(
        self, relative_path: str, content: str
    ) -> tuple[bool, Any, ConfigurationIssue | None]:
        extension = Path(relative_path).suffix.lower()
        filename = Path(relative_path).name.lower()

        try:
            if extension == ".json":
                return True, json.loads(content), None

            if extension == ".toml":
                return True, tomllib.loads(content), None

            if extension in {".ini", ".cfg", ".conf"} or filename in {
                "pytest.ini",
                ".flake8",
                "mypy.ini",
                ".coveragerc",
            }:
                parser = configparser.ConfigParser()
                parser.read_string(content)
                data = {
                    section: dict(parser.items(section))
                    for section in parser.sections()
                }
                return True, data, None

            if extension in {".yaml", ".yml"}:
                if importlib.util.find_spec("yaml") is None:
                    return (
                        False,
                        None,
                        ConfigurationIssue(
                            code="YAML_PARSER_UNAVAILABLE",
                            message=(
                                "PyYAML is required to validate YAML files. "
                                "Install it with 'pip install PyYAML'."
                            ),
                            path=relative_path,
                        ),
                    )

                import yaml

                data = yaml.safe_load(content)
                return True, data, None

            if extension == ".env" or filename == ".env":
                return True, self._parse_env(content), None

            return (
                False,
                None,
                ConfigurationIssue(
                    code="UNSUPPORTED_CONFIG_FORMAT",
                    message="Configuration file format is not supported.",
                    path=relative_path,
                    severity=ConfigurationIssueSeverity.WARNING,
                ),
            )

        except (json.JSONDecodeError, tomllib.TOMLDecodeError,
                configparser.Error, UnicodeError, ValueError) as exc:
            return (
                False,
                None,
                ConfigurationIssue(
                    code="INVALID_CONFIG_SYNTAX",
                    message=f"Configuration syntax is invalid: {exc}",
                    path=relative_path,
                ),
            )
        except Exception as exc:
            # Parser-specific errors, including YAML parser errors.
            return (
                False,
                None,
                ConfigurationIssue(
                    code="INVALID_CONFIG_SYNTAX",
                    message=f"Configuration could not be parsed: {exc}",
                    path=relative_path,
                ),
            )

    @staticmethod
    def _parse_env(content: str) -> dict[str, str]:
        values: dict[str, str] = {}

        for line_number, raw_line in enumerate(content.splitlines(), start=1):
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue

            if line.startswith("export "):
                line = line[7:].strip()

            if "=" not in line:
                raise ValueError(
                    f"Invalid environment variable assignment on line {line_number}."
                )

            key, value = line.split("=", 1)
            key = key.strip()
            if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key):
                raise ValueError(
                    f"Invalid environment variable name on line {line_number}."
                )

            if key in values:
                raise ValueError(
                    f"Duplicate environment variable '{key}' on line {line_number}."
                )

            values[key] = value.strip().strip("'\"")

        return values

    @staticmethod
    def _has_dotted_key(data: Any, dotted_key: str) -> bool:
        current = data
        for part in dotted_key.split("."):
            if not isinstance(current, Mapping) or part not in current:
                return False
            current = current[part]
        return True
