
from dataclasses import dataclass

from app.application.dependency_analyzer import (
    DependencyAnalyzer,
    DependencyAnalyzerError,
    DependencyRecord,
)
from app.application.import_analyzer import ImportRecord


class DependencyContextError(ValueError):
    """Raised when dependency context construction fails."""


@dataclass(frozen=True)
class DependencyContextResult:
    """Contains dependency information relevant to a repository question."""

    total_dependencies: int
    dependencies: tuple
    dependencies_by_file: dict
    dependency_counts: dict

    def __post_init__(self):
        if (
            not isinstance(self.total_dependencies, int)
            or isinstance(self.total_dependencies, bool)
            or self.total_dependencies < 0
        ):
            raise DependencyContextError(
                "Total dependencies must be a non-negative integer."
            )

        if not isinstance(self.dependencies, tuple):
            raise DependencyContextError(
                "Dependencies must be a tuple."
            )

        if self.total_dependencies != len(self.dependencies):
            raise DependencyContextError(
                "Total dependencies must match the dependency count."
            )

        if not all(
            isinstance(item, DependencyRecord)
            for item in self.dependencies
        ):
            raise DependencyContextError(
                "Every dependency must be a DependencyRecord."
            )

        if not isinstance(self.dependencies_by_file, dict):
            raise DependencyContextError(
                "Dependencies by file must be a dictionary."
            )

        if not isinstance(self.dependency_counts, dict):
            raise DependencyContextError(
                "Dependency counts must be a dictionary."
            )


class DependencyContextService:
    """Build structured dependency context from repository imports."""

    def __init__(self, dependency_analyzer=None):
        if dependency_analyzer is None:
            dependency_analyzer = DependencyAnalyzer()

        if not isinstance(dependency_analyzer, DependencyAnalyzer):
            raise DependencyContextError(
                "Dependency analyzer must be a DependencyAnalyzer instance."
            )

        self.dependency_analyzer = dependency_analyzer

    def retrieve(
        self,
        imports,
        internal_modules=(),
        relevant_files=None,
    ):
        """Classify and organize dependencies for relevant repository files."""

        self._validate_imports(imports)
        self._validate_internal_modules(internal_modules)

        if relevant_files is not None:
            self._validate_relevant_files(relevant_files)

        try:
            import_records = tuple(imports)
            known_modules = tuple(internal_modules)

            dependencies = self.dependency_analyzer.analyze(
                imports=import_records,
                internal_modules=known_modules,
            )

            if relevant_files is not None:
                relevant_file_names = set(relevant_files)

                dependencies = tuple(
                    dependency
                    for dependency in dependencies
                    if dependency.source_file in relevant_file_names
                )

            return self._build_result(dependencies)

        except DependencyAnalyzerError as exc:
            raise DependencyContextError(
                "Unable to analyze repository dependencies."
            ) from exc
        except DependencyContextError:
            raise
        except Exception as exc:
            raise DependencyContextError(
                "Unable to construct dependency context."
            ) from exc

    def retrieve_by_file(
        self,
        imports,
        filename,
        internal_modules=(),
    ):
        """Retrieve dependencies belonging to one source file."""

        if not isinstance(filename, str) or not filename.strip():
            raise DependencyContextError(
                "Filename must be a non-empty string."
            )

        return self.retrieve(
            imports=imports,
            internal_modules=internal_modules,
            relevant_files=(filename,),
        )

    @staticmethod
    def _build_result(dependencies):
        dependencies_by_file = {}
        dependency_counts = {
            DependencyAnalyzer.DEPENDENCY_INTERNAL: 0,
            DependencyAnalyzer.DEPENDENCY_EXTERNAL: 0,
            DependencyAnalyzer.DEPENDENCY_STANDARD_LIBRARY: 0,
            DependencyAnalyzer.DEPENDENCY_UNRESOLVED: 0,
        }

        for dependency in dependencies:
            dependencies_by_file.setdefault(
                dependency.source_file,
                [],
            ).append(dependency)

            dependency_counts[dependency.dependency_type] = (
                dependency_counts.get(dependency.dependency_type, 0) + 1
            )

        return DependencyContextResult(
            total_dependencies=len(dependencies),
            dependencies=tuple(dependencies),
            dependencies_by_file={
                filename: tuple(records)
                for filename, records in sorted(
                    dependencies_by_file.items()
                )
            },
            dependency_counts=dependency_counts,
        )

    @staticmethod
    def _validate_imports(imports):
        if imports is None or isinstance(
            imports,
            (str, bytes, dict),
        ):
            raise DependencyContextError(
                "Imports must be an iterable of ImportRecord objects."
            )

        try:
            records = tuple(imports)
        except TypeError as exc:
            raise DependencyContextError(
                "Imports must be iterable."
            ) from exc

        if not all(
            isinstance(record, ImportRecord)
            for record in records
        ):
            raise DependencyContextError(
                "Every import must be an ImportRecord."
            )

    @staticmethod
    def _validate_internal_modules(internal_modules):
        if internal_modules is None or isinstance(
            internal_modules,
            (str, bytes, dict),
        ):
            raise DependencyContextError(
                "Internal modules must be an iterable of module names."
            )

        try:
            modules = tuple(internal_modules)
        except TypeError as exc:
            raise DependencyContextError(
                "Internal modules must be iterable."
            ) from exc

        if not all(
            isinstance(module, str) and module.strip()
            for module in modules
        ):
            raise DependencyContextError(
                "Every internal module must be a non-empty string."
            )

    @staticmethod
    def _validate_relevant_files(relevant_files):
        if isinstance(
            relevant_files,
            (str, bytes, dict),
        ):
            raise DependencyContextError(
                "Relevant files must be an iterable of filenames."
            )

        try:
            filenames = tuple(relevant_files)
        except TypeError as exc:
            raise DependencyContextError(
                "Relevant files must be iterable."
            ) from exc

        if not all(
            isinstance(filename, str) and filename.strip()
            for filename in filenames
        ):
            raise DependencyContextError(
                "Every relevant filename must be a non-empty string."
            )
