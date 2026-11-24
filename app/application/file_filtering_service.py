
from app.application.repository_scanner import RepositoryScanResult
from app.application.ignore_rule_service import (
    IgnoreRuleService,
    IgnoreRuleError,
)


class FileFilteringService:
    """Applies repository ignore rules to discovered entries."""

    def __init__(self, ignore_rule_service=None):
        self.ignore_rule_service = (
            ignore_rule_service or IgnoreRuleService()
        )

    def filter_files(
        self,
        scan_result: RepositoryScanResult,
        ignored_directories=None,
        ignored_files=None,
        respect_gitignore=True,
    ) -> RepositoryScanResult:
        """Return a filtered copy of the repository scan result."""

        if not isinstance(scan_result, RepositoryScanResult):
            raise IgnoreRuleError(
                "A valid RepositoryScanResult object is required."
            )

        return self.ignore_rule_service.filter_scan_result(
            result=scan_result,
            ignored_directories=ignored_directories,
            ignored_files=ignored_files,
            respect_gitignore=respect_gitignore,
        )

    @staticmethod
    def get_filter_statistics(
        original: RepositoryScanResult,
        filtered: RepositoryScanResult,
    ) -> dict:
        """Compare original and filtered discovery statistics."""

        if not isinstance(original, RepositoryScanResult):
            raise ValueError("Invalid original scan result.")

        if not isinstance(filtered, RepositoryScanResult):
            raise ValueError("Invalid filtered scan result.")

        return {
            "original_files": original.total_files,
            "filtered_files": filtered.total_files,
            "ignored_files": (
                original.total_files - filtered.total_files
            ),
            "original_directories": original.total_directories,
            "filtered_directories": filtered.total_directories,
            "ignored_directories": (
                original.total_directories
                - filtered.total_directories
            ),
            "original_symlinks": original.total_symlinks,
            "filtered_symlinks": filtered.total_symlinks,
            "ignored_symlinks": (
                original.total_symlinks
                - filtered.total_symlinks
            ),
        }
