
from pathlib import Path
from typing import Callable

from appy.application.repository_discovery_integration_service import (
    RepositoryDiscoveryIntegrationService,
)
from appy.application.source_file_selection_service import (
    SourceFileSelectionService,
)
from appy.application.language_parser_factory import (
    LanguageParserFactory,
)
from appy.application.code_entity_extractor import CodeEntityExtractor
from appy.application.code_indexing_service import CodeIndexingService
from appy.application.import_analyzer import ImportAnalyzer
from appy.application.call_graph_service import CallGraphService
from appy.application.inheritance_analyzer import InheritanceAnalyzer

from appy.application.question_analysis_agent import (
    QuestionAnalysisAgent,
)
from appy.application.repository_retrieval_service import (
    RepositoryRetrievalService,
)
from appy.application.relevant_file_retrieval_service import (
    RelevantFileRetrievalService,
)
from appy.application.relevant_code_retrieval_service import (
    RelevantCodeRetrievalService,
)
from appy.application.dependency_context_service import (
    DependencyContextService,
)
from appy.application.architecture_context_service import (
    ArchitectureContextService,
)
from appy.application.context_builder import ContextBuilder

from appy.application.codebase_reasoning_service import (
    CodebaseReasoningService,
)
from appy.application.reasoning_response_model import (
    ReasoningResponse,
)


class ReasoningOrchestrationError(RuntimeError):
    """Raised when reasoning orchestration fails."""


class ReasoningOrchestrationService:
    """
    Coordinates repository intelligence retrieval and AI reasoning.

    The service reuses the existing repository discovery, parsing,
    indexing, retrieval, context construction, and reasoning services.
    """

    def __init__(
        self,
        repository_retrieval_service: RepositoryRetrievalService,
        relevant_file_retrieval_service: RelevantFileRetrievalService,
        relevant_code_retrieval_service: RelevantCodeRetrievalService,
        dependency_context_service: DependencyContextService,
        architecture_context_service: ArchitectureContextService,
        ai_service_factory: Callable,
        repository_discovery_service=None,
        source_file_selection_service=None,
        language_parser_factory=None,
        code_entity_extractor=None,
        code_indexing_service=None,
        import_analyzer=None,
        call_graph_service=None,
        inheritance_analyzer=None,
        question_analysis_agent=None,
        context_builder=None,
        reasoning_service_factory: Callable | None = None,
    ):
        self.repository_discovery_service = (
            repository_discovery_service
            or RepositoryDiscoveryIntegrationService()
        )

        self.source_file_selection_service = (
            source_file_selection_service
            or SourceFileSelectionService()
        )

        self.language_parser_factory = (
            language_parser_factory
            or LanguageParserFactory()
        )

        self.code_entity_extractor = (
            code_entity_extractor
            or CodeEntityExtractor()
        )

        self.code_indexing_service = (
            code_indexing_service
            or CodeIndexingService()
        )

        self.import_analyzer = import_analyzer or ImportAnalyzer()
        self.call_graph_service = call_graph_service or CallGraphService()

        self.inheritance_analyzer = (
            inheritance_analyzer or InheritanceAnalyzer()
        )

        self.question_analysis_agent = (
            question_analysis_agent or QuestionAnalysisAgent()
        )

        self.repository_retrieval_service = repository_retrieval_service
        self.relevant_file_retrieval_service = (
            relevant_file_retrieval_service
        )
        self.relevant_code_retrieval_service = (
            relevant_code_retrieval_service
        )
        self.dependency_context_service = dependency_context_service
        self.architecture_context_service = architecture_context_service

        self.context_builder = context_builder or ContextBuilder()

        if not callable(ai_service_factory):
            raise ReasoningOrchestrationError(
                "AI service factory must be callable."
            )

        if reasoning_service_factory is not None and not callable(
            reasoning_service_factory
        ):
            raise ReasoningOrchestrationError(
                "Reasoning service factory must be callable."
            )

        self.ai_service_factory = ai_service_factory

        # Production uses the real reasoning service by default.
        # Tests or alternative configurations can inject a factory.
        self.reasoning_service_factory = (
            reasoning_service_factory or CodebaseReasoningService
        )

    def answer_question(
        self,
        repository_path: str | Path,
        repository_id: str,
        question: str,
        provider_name: str,
        model: str,
        max_context_characters: int = 12000,
        relevant_file_limit: int = 10,
        relevant_code_limit: int = 50,
        memory_limit: int = 10,
    ) -> ReasoningResponse:
        """
        Execute the complete repository question-answering workflow.
        """

        self._validate_request(
            repository_path=repository_path,
            repository_id=repository_id,
            question=question,
            provider_name=provider_name,
            model=model,
            max_context_characters=max_context_characters,
            relevant_file_limit=relevant_file_limit,
            relevant_code_limit=relevant_code_limit,
            memory_limit=memory_limit,
        )

        try:
            # 1. Understand the user's question.
            question_analysis = self.question_analysis_agent.analyze(
                question
            )

            # 2. Discover the repository.
            discovery_result = self.repository_discovery_service.discover(
                repository_path=repository_path,
                save_index=True,
            )

            repository_info = discovery_result.repository
            repository_map = discovery_result.repository_map

            # 3. Select supported source files.
            selection_result = (
                self.source_file_selection_service.select_source_files(
                    discovery_result.metadata.get("files", ())
                )
            )

            # 4. Parse source files and extract code intelligence.
            entities = []
            imports = []
            call_graph_results = []
            inheritance_results = []

            for file_metadata in selection_result.files:
                relative_path = file_metadata.relative_path
                language = file_metadata.language

                try:
                    parser = self.language_parser_factory.get_parser(
                        language
                    )
                except Exception:
                    # A selected file may not have a registered parser.
                    continue

                source_path = repository_info.root / relative_path

                try:
                    source_code = source_path.read_text(
                        encoding="utf-8",
                        errors="replace",
                    )

                    parsed_source = parser.parse(
                        source_code,
                        filename=relative_path,
                    )

                    entities.extend(
                        self.code_entity_extractor.extract(
                            parsed_source
                        )
                    )

                    imports.extend(
                        self.import_analyzer.analyze(parsed_source)
                    )

                    call_graph_results.append(
                        self.call_graph_service.analyze(parsed_source)
                    )

                    inheritance_results.append(
                        self.inheritance_analyzer.analyze(parsed_source)
                    )

                except Exception:
                    # A malformed or unreadable file should not prevent
                    # analysis of the remaining repository files.
                    continue

            # 5. Build the searchable code index.
            code_index = self.code_indexing_service.build_index(
                entities
            )

            internal_modules = tuple(
                entity.name
                for entity in entities
                if entity.entity_type == "module"
            )

            # 6. Retrieve repository memories.
            repository_result = (
                self.repository_retrieval_service.retrieve(
                    repository_id=repository_id,
                    analysis_result=question_analysis,
                    limit=memory_limit,
                )
            )

            # 7. Retrieve relevant files.
            relevant_files = (
                self.relevant_file_retrieval_service.retrieve(
                    index=code_index,
                    analysis_result=question_analysis,
                    limit=relevant_file_limit,
                )
            )

            # 8. Retrieve relevant code entities.
            relevant_code = (
                self.relevant_code_retrieval_service.retrieve(
                    index=code_index,
                    relevant_files=relevant_files,
                    limit=relevant_code_limit,
                )
            )

            relevant_filenames = tuple(
                item.filename
                for item in relevant_files.files
            )

            # 9. Build dependency context.
            dependency_context = (
                self.dependency_context_service.retrieve(
                    imports=imports,
                    internal_modules=internal_modules,
                    relevant_files=relevant_filenames,
                )
            )

            # 10. Build architecture context.
            architecture_context = (
                self.architecture_context_service.build_context(
                    repository_info=repository_info,
                    directory_tree=repository_map,
                    call_graph_results=tuple(call_graph_results),
                    inheritance_results=tuple(inheritance_results),
                    relevant_files=relevant_filenames,
                )
            )

            # 11. Combine all retrieved information.
            combined_context = self.context_builder.build_context(
                question_analysis=question_analysis,
                repository_result=repository_result,
                relevant_files=relevant_files,
                relevant_code=relevant_code,
                dependency_context=dependency_context,
                architecture_context=architecture_context,
                max_characters=max_context_characters,
            )

            # 12. Create the selected AI provider service.
            ai_service = self.ai_service_factory(provider_name)

            # 13. Create the reasoning service using the configured factory.
            reasoning_service = self.reasoning_service_factory(
                ai_service=ai_service
            )

            # 14. Generate the answer.
            answer = reasoning_service.generate_answer(
                question=question_analysis.question,
                context=combined_context,
                model=model,
            )

            # 15. Determine whether retrieved evidence exists.
            memory_count = len(
                repository_result.retrieval_data.memories
            )

            evidence_sufficient = bool(
                relevant_files.files
                or relevant_code.code_entities
                or memory_count
            )

            # 16. Return the validated response.
            return ReasoningResponse(
                question=question_analysis.question,
                answer=answer,
                intent=question_analysis.intent,
                source_files=combined_context.source_files,
                entity_ids=combined_context.entity_ids,
                provider_name=reasoning_service.provider_name,
                model_name=model,
                evidence_sufficient=evidence_sufficient,
            )

        except ReasoningOrchestrationError:
            raise

        except Exception as exc:
            raise ReasoningOrchestrationError(
                "Unable to complete repository reasoning."
            ) from exc

    @staticmethod
    def _validate_request(
        repository_path,
        repository_id,
        question,
        provider_name,
        model,
        max_context_characters,
        relevant_file_limit,
        relevant_code_limit,
        memory_limit,
    ):
        """Validate orchestration request arguments."""

        if not isinstance(repository_path, (str, Path)):
            raise ReasoningOrchestrationError(
                "Repository path must be a string or Path."
            )

        if isinstance(repository_path, str) and not repository_path.strip():
            raise ReasoningOrchestrationError(
                "Repository path cannot be empty."
            )

        if not isinstance(repository_id, str) or not repository_id.strip():
            raise ReasoningOrchestrationError(
                "Repository ID must be a non-empty string."
            )

        if not isinstance(question, str) or not question.strip():
            raise ReasoningOrchestrationError(
                "Question must be a non-empty string."
            )

        if not isinstance(provider_name, str) or not provider_name.strip():
            raise ReasoningOrchestrationError(
                "Provider name must be a non-empty string."
            )

        if not isinstance(model, str) or not model.strip():
            raise ReasoningOrchestrationError(
                "Model must be a non-empty string."
            )

        positive_values = {
            "Maximum context characters": max_context_characters,
            "Relevant file limit": relevant_file_limit,
            "Relevant code limit": relevant_code_limit,
            "Memory limit": memory_limit,
        }

        for label, value in positive_values.items():
            if (
                isinstance(value, bool)
                or not isinstance(value, int)
                or value < 1
            ):
                raise ReasoningOrchestrationError(
                    f"{label} must be a positive integer."
                )
