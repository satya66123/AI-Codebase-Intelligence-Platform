
from dataclasses import dataclass

from app.application.repository_input import RepositoryInfo
from app.application.call_graph_service import (
    CallGraphResult,
    CallRecord,
)
from app.application.inheritance_analyzer import (
    InheritanceAnalysisResult,
    InheritanceRecord,
)


class ArchitectureContextError(ValueError):
    """Raised when architecture context construction fails."""


@dataclass(frozen=True)
class ArchitectureContextResult:
    """Structured architecture information for a repository."""

    repository_name: str
    repository_root: str
    is_git_repository: bool
    directory_tree: str
    call_graphs: tuple
    inheritance_analyses: tuple
    total_calls: int
    total_inheritance_relationships: int
    classes_without_bases: tuple

    def __post_init__(self):
        if not isinstance(self.repository_name, str) or not self.repository_name.strip():
            raise ArchitectureContextError(
                "Repository name must be a non-empty string."
            )

        if not isinstance(self.repository_root, str) or not self.repository_root.strip():
            raise ArchitectureContextError(
                "Repository root must be a non-empty string."
            )

        if not isinstance(self.is_git_repository, bool):
            raise ArchitectureContextError(
                "Git repository status must be a boolean."
            )

        if not isinstance(self.directory_tree, str) or not self.directory_tree.strip():
            raise ArchitectureContextError(
                "Directory tree must be a non-empty string."
            )

        if not isinstance(self.call_graphs, tuple):
            raise ArchitectureContextError(
                "Call graphs must be provided as a tuple."
            )

        if not all(
            isinstance(item, CallGraphResult)
            for item in self.call_graphs
        ):
            raise ArchitectureContextError(
                "Every call graph must be a CallGraphResult."
            )

        if not isinstance(self.inheritance_analyses, tuple):
            raise ArchitectureContextError(
                "Inheritance analyses must be provided as a tuple."
            )

        if not all(
            isinstance(item, InheritanceAnalysisResult)
            for item in self.inheritance_analyses
        ):
            raise ArchitectureContextError(
                "Every inheritance analysis must be an InheritanceAnalysisResult."
            )

        if (
            not isinstance(self.total_calls, int)
            or isinstance(self.total_calls, bool)
            or self.total_calls < 0
        ):
            raise ArchitectureContextError(
                "Total calls must be a non-negative integer."
            )

        if (
            not isinstance(self.total_inheritance_relationships, int)
            or isinstance(self.total_inheritance_relationships, bool)
            or self.total_inheritance_relationships < 0
        ):
            raise ArchitectureContextError(
                "Total inheritance relationships must be a non-negative integer."
            )

        if self.total_calls != sum(
            graph.total_calls for graph in self.call_graphs
        ):
            raise ArchitectureContextError(
                "Total calls must match the call graph results."
            )

        if self.total_inheritance_relationships != sum(
            analysis.total_relationships
            for analysis in self.inheritance_analyses
        ):
            raise ArchitectureContextError(
                "Total inheritance relationships must match the analysis results."
            )

        if not isinstance(self.classes_without_bases, tuple):
            raise ArchitectureContextError(
                "Classes without bases must be provided as a tuple."
            )

        if not all(
            isinstance(name, str) and name.strip()
            for name in self.classes_without_bases
        ):
            raise ArchitectureContextError(
                "Class names without bases must be non-empty strings."
            )


class ArchitectureContextService:
    """Build structured architecture context from existing analysis results."""

    def build_context(
        self,
        repository_info,
        directory_tree,
        call_graph_results=(),
        inheritance_results=(),
        relevant_files=None,
    ):
        """Combine repository structure, call graphs, and inheritance data."""

        self._validate_repository_info(repository_info)
        self._validate_directory_tree(directory_tree)
        self._validate_call_graph_results(call_graph_results)
        self._validate_inheritance_results(inheritance_results)

        if relevant_files is not None:
            self._validate_relevant_files(relevant_files)

        try:
            call_graphs = tuple(call_graph_results)
            inheritance_analyses = tuple(inheritance_results)

            if relevant_files is not None:
                selected_files = set(relevant_files)

                call_graphs = tuple(
                    graph
                    for graph in call_graphs
                    if graph.filename in selected_files
                )

                inheritance_analyses = tuple(
                    analysis
                    for analysis in inheritance_analyses
                    if analysis.filename in selected_files
                )

            total_calls = sum(
                graph.total_calls for graph in call_graphs
            )

            total_inheritance = sum(
                analysis.total_relationships
                for analysis in inheritance_analyses
            )

            classes_without_bases = tuple(
                class_name
                for analysis in inheritance_analyses
                for class_name in analysis.classes_without_bases
            )

            return ArchitectureContextResult(
                repository_name=repository_info.name,
                repository_root=str(repository_info.root),
                is_git_repository=repository_info.is_git_repository,
                directory_tree=directory_tree,
                call_graphs=call_graphs,
                inheritance_analyses=inheritance_analyses,
                total_calls=total_calls,
                total_inheritance_relationships=total_inheritance,
                classes_without_bases=classes_without_bases,
            )

        except ArchitectureContextError:
            raise
        except Exception as exc:
            raise ArchitectureContextError(
                "Unable to build architecture context."
            ) from exc

    @staticmethod
    def _validate_repository_info(repository_info):
        if not isinstance(repository_info, RepositoryInfo):
            raise ArchitectureContextError(
                "Repository information must be a RepositoryInfo instance."
            )

    @staticmethod
    def _validate_directory_tree(directory_tree):
        if (
            not isinstance(directory_tree, str)
            or not directory_tree.strip()
        ):
            raise ArchitectureContextError(
                "Directory tree must be a non-empty string."
            )

    @staticmethod
    def _validate_call_graph_results(results):
        if results is None or isinstance(
            results,
            (str, bytes, dict),
        ):
            raise ArchitectureContextError(
                "Call graph results must be an iterable of CallGraphResult objects."
            )

        try:
            graphs = tuple(results)
        except TypeError as exc:
            raise ArchitectureContextError(
                "Call graph results must be iterable."
            ) from exc

        if not all(
            isinstance(graph, CallGraphResult)
            for graph in graphs
        ):
            raise ArchitectureContextError(
                "Every call graph result must be a CallGraphResult."
            )

        for graph in graphs:
            if not isinstance(graph.calls, tuple):
                raise ArchitectureContextError(
                    "Call graph calls must be provided as a tuple."
                )

            if not all(
                isinstance(call, CallRecord)
                for call in graph.calls
            ):
                raise ArchitectureContextError(
                    "Every call graph entry must be a CallRecord."
                )

            if graph.total_calls != len(graph.calls):
                raise ArchitectureContextError(
                    "Call graph total must match its calls."
                )

    @staticmethod
    def _validate_inheritance_results(results):
        if results is None or isinstance(
            results,
            (str, bytes, dict),
        ):
            raise ArchitectureContextError(
                "Inheritance results must be an iterable of InheritanceAnalysisResult objects."
            )

        try:
            analyses = tuple(results)
        except TypeError as exc:
            raise ArchitectureContextError(
                "Inheritance results must be iterable."
            ) from exc

        if not all(
            isinstance(analysis, InheritanceAnalysisResult)
            for analysis in analyses
        ):
            raise ArchitectureContextError(
                "Every inheritance result must be an InheritanceAnalysisResult."
            )

        for analysis in analyses:
            if not isinstance(analysis.relationships, tuple):
                raise ArchitectureContextError(
                    "Inheritance relationships must be a tuple."
                )

            if not all(
                isinstance(item, InheritanceRecord)
                for item in analysis.relationships
            ):
                raise ArchitectureContextError(
                    "Every inheritance relationship must be an InheritanceRecord."
                )

            if not isinstance(analysis.classes_without_bases, tuple):
                raise ArchitectureContextError(
                    "Classes without bases must be a tuple."
                )

            if analysis.total_relationships != len(
                analysis.relationships
            ):
                raise ArchitectureContextError(
                    "Inheritance total must match its relationships."
                )

    @staticmethod
    def _validate_relevant_files(relevant_files):
        if isinstance(
            relevant_files,
            (str, bytes, dict),
        ):
            raise ArchitectureContextError(
                "Relevant files must be an iterable of filenames."
            )

        try:
            filenames = tuple(relevant_files)
        except TypeError as exc:
            raise ArchitectureContextError(
                "Relevant files must be iterable."
            ) from exc

        if not all(
            isinstance(filename, str) and filename.strip()
            for filename in filenames
        ):
            raise ArchitectureContextError(
                "Every relevant filename must be a non-empty string."
            )
