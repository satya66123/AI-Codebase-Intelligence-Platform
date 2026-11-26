"""Load and parse supported source files from a discovered repository."""

from dataclasses import asdict, dataclass, is_dataclass
from pathlib import Path
from typing import Any, Mapping

from appy.application.language_parser_factory import (
    LanguageParserFactory,
    LanguageParserFactoryError,
)
from appy.application.source_file_selection_service import (
    SourceFileSelectionService,
)


class RepositorySourceLoadingError(RuntimeError):
    """Raised when repository source loading cannot be completed."""

    def __init__(self, message: str, stage: str = "source_loading") -> None:
        super().__init__(message)
        self.stage = stage


@dataclass(frozen=True)
class SourceFileLoadFailure:
    """Describe a source file that could not be loaded or parsed."""

    filename: str
    language: str
    stage: str
    reason: str


@dataclass(frozen=True)
class RepositorySourceLoadingResult:
    """Contain loaded source files and successfully parsed sources."""

    repository_path: str
    source_files: Mapping[str, str]
    parsed_sources: Mapping[str, Any]
    selected_file_count: int
    parsed_file_count: int
    skipped_file_count: int
    language_counts: Mapping[str, int]
    failures: tuple[SourceFileLoadFailure, ...]

    @property
    def is_successful(self) -> bool:
        """Return whether at least one source file was parsed."""

        return self.parsed_file_count > 0

    @property
    def failed_file_count(self) -> int:
        """Return the number of files that failed loading or parsing."""

        return len(self.failures)


class RepositorySourceLoadingService:
    """Load repository source files and parse them with registered parsers."""

    def __init__(
        self,
        source_file_selection_service: SourceFileSelectionService | None = None,
        language_parser_factory: LanguageParserFactory | None = None,
        max_file_size_bytes: int = 2_000_000,
    ) -> None:
        if (
            isinstance(max_file_size_bytes, bool)
            or not isinstance(max_file_size_bytes, int)
            or max_file_size_bytes <= 0
        ):
            raise RepositorySourceLoadingError(
                "max_file_size_bytes must be a positive integer.",
                stage="configuration",
            )

        self.source_file_selection_service = (
            source_file_selection_service
            if source_file_selection_service is not None
            else SourceFileSelectionService()
        )
        self.language_parser_factory = (
            language_parser_factory
            if language_parser_factory is not None
            else LanguageParserFactory()
        )
        self.max_file_size_bytes = max_file_size_bytes

    def load_and_parse(
        self,
        repository_path: str | Path,
        file_metadata: Any,
        languages: Any = None,
    ) -> RepositorySourceLoadingResult:
        """Load and parse supported files from repository metadata."""

        root = self._validate_repository_path(repository_path)

        try:
            selection = self.source_file_selection_service.select_source_files(
                file_metadata,
                languages=languages,
            )
        except Exception as exc:
            raise RepositorySourceLoadingError(
                f"Unable to select repository source files: {exc}",
                stage="file_selection",
            ) from exc

        source_files: dict[str, str] = {}
        parsed_sources: dict[str, Any] = {}
        failures: list[SourceFileLoadFailure] = []

        for record in selection.files:
            metadata = self._normalize_record(record)
            relative_path = self._get_relative_path(metadata)
            language = self._get_language(metadata, relative_path)

            if not relative_path:
                failures.append(
                    SourceFileLoadFailure(
                        filename="<unknown>",
                        language=language,
                        stage="metadata",
                        reason="File metadata does not contain a relative path.",
                    )
                )
                continue

            try:
                source_path = self._resolve_source_path(root, relative_path)
                source_code = self._read_source_file(source_path)
                source_files[relative_path] = source_code
            except Exception as exc:
                failures.append(
                    SourceFileLoadFailure(
                        filename=relative_path,
                        language=language,
                        stage="loading",
                        reason=str(exc),
                    )
                )
                continue

            try:
                parser = self.language_parser_factory.get_parser(language)
            except LanguageParserFactoryError as exc:
                failures.append(
                    SourceFileLoadFailure(
                        filename=relative_path,
                        language=language,
                        stage="parser_lookup",
                        reason=str(exc),
                    )
                )
                continue
            except Exception as exc:
                failures.append(
                    SourceFileLoadFailure(
                        filename=relative_path,
                        language=language,
                        stage="parser_lookup",
                        reason=str(exc),
                    )
                )
                continue

            try:
                parsed_sources[relative_path] = parser.parse(
                    source_code,
                    filename=relative_path,
                )
            except Exception as exc:
                failures.append(
                    SourceFileLoadFailure(
                        filename=relative_path,
                        language=language,
                        stage="parsing",
                        reason=str(exc),
                    )
                )

        return RepositorySourceLoadingResult(
            repository_path=str(root),
            source_files=dict(source_files),
            parsed_sources=dict(parsed_sources),
            selected_file_count=selection.selected_count,
            parsed_file_count=len(parsed_sources),
            skipped_file_count=selection.skipped_count,
            language_counts=dict(selection.languages),
            failures=tuple(failures),
        )

    @staticmethod
    def _validate_repository_path(repository_path: str | Path) -> Path:
        if not isinstance(repository_path, (str, Path)):
            raise RepositorySourceLoadingError(
                "repository_path must be a string or Path.",
                stage="input_validation",
            )

        if isinstance(repository_path, str) and not repository_path.strip():
            raise RepositorySourceLoadingError(
                "repository_path cannot be empty.",
                stage="input_validation",
            )

        root = Path(repository_path).expanduser()

        try:
            root = root.resolve(strict=True)
        except (OSError, RuntimeError) as exc:
            raise RepositorySourceLoadingError(
                f"Repository path cannot be resolved: {exc}",
                stage="input_validation",
            ) from exc

        if not root.is_dir():
            raise RepositorySourceLoadingError(
                "repository_path must point to an existing directory.",
                stage="input_validation",
            )

        return root

    @staticmethod
    def _normalize_record(record: Any) -> dict:
        if is_dataclass(record) and not isinstance(record, type):
            return asdict(record)

        if isinstance(record, Mapping):
            return dict(record)

        if hasattr(record, "__dict__"):
            return vars(record)

        raise RepositorySourceLoadingError(
            "Source file metadata must be a mapping or metadata object.",
            stage="metadata",
        )

    @staticmethod
    def _get_relative_path(metadata: Mapping[str, Any]) -> str:
        value = metadata.get("relative_path")

        if not isinstance(value, str) or not value.strip():
            return ""

        return value.strip()

    @staticmethod
    def _get_language(metadata: Mapping[str, Any], relative_path: str) -> str:
        language = metadata.get("language")

        if isinstance(language, str) and language.strip():
            return language.strip()

        extension = Path(relative_path).suffix.casefold()

        return SourceFileSelectionService.SUPPORTED_EXTENSIONS.get(
            extension,
            "Unknown",
        )

    @staticmethod
    def _resolve_source_path(root: Path, relative_path: str) -> Path:
        candidate = Path(relative_path)

        if candidate.is_absolute():
            raise RepositorySourceLoadingError(
                "Absolute source paths are not allowed.",
                stage="path_validation",
            )

        resolved = (root / candidate).resolve(strict=True)

        try:
            resolved.relative_to(root)
        except ValueError as exc:
            raise RepositorySourceLoadingError(
                "Source file path escapes the repository directory.",
                stage="path_validation",
            ) from exc

        if not resolved.is_file():
            raise RepositorySourceLoadingError(
                "Source path does not point to a file.",
                stage="path_validation",
            )

        return resolved

    def _read_source_file(self, source_path: Path) -> str:
        try:
            file_size = source_path.stat().st_size
        except OSError as exc:
            raise RepositorySourceLoadingError(
                f"Unable to inspect source file: {exc}",
                stage="loading",
            ) from exc

        if file_size > self.max_file_size_bytes:
            raise RepositorySourceLoadingError(
                (
                    f"File exceeds the configured size limit of "
                    f"{self.max_file_size_bytes} bytes."
                ),
                stage="loading",
            )

        try:
            return source_path.read_text(
                encoding="utf-8",
                errors="replace",
            )
        except OSError as exc:
            raise RepositorySourceLoadingError(
                f"Unable to read source file: {exc}",
                stage="loading",
            ) from exc