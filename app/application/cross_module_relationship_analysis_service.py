
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Mapping

from app.application.call_graph_service import (
    CallGraphError,
    CallGraphService,
    CallRecord,
)
from app.application.code_entity_extractor import (
    CodeEntity,
    CodeEntityExtractionError,
    CodeEntityExtractor,
)
from app.application.language_parser import ParsedSource


class CrossModuleRelationshipAnalysisError(ValueError):
    """Raised when cross-module relationship analysis fails."""


class CrossModuleRelationshipType:
    """Relationship classifications."""

    FUNCTION_CALL = "function_call"
    METHOD_CALL = "method_call"


class CrossModuleResolutionStatus:
    """Resolution states for cross-module references."""

    RESOLVED = "resolved"
    UNRESOLVED = "unresolved"
    AMBIGUOUS = "ambiguous"


@dataclass(frozen=True)
class CrossModuleCall:
    """Represents a call from one repository module to another."""

    source_module: str
    target_module: str | None
    source_file: str
    target_file: str | None
    caller: str
    callee: str
    caller_type: str
    call_type: str
    relationship_type: str
    line: int
    resolution_status: str
    target_entity: str | None = None


@dataclass(frozen=True)
class ModuleRelationship:
    """Aggregated relationship between two repository modules."""

    source_module: str
    target_module: str
    relationship_count: int
    relationship_types: tuple[str, ...]
    calls: tuple[CrossModuleCall, ...]


@dataclass(frozen=True)
class UnresolvedCrossModuleReference:
    """A possible cross-module call that could not be resolved."""

    source_module: str
    source_file: str
    caller: str
    callee: str
    line: int
    reason: str


@dataclass(frozen=True)
class CrossModuleRelationshipAnalysisResult:
    """Complete cross-module relationship analysis result."""

    total_files: int
    analyzed_files: int
    skipped_files: int
    total_modules: int
    total_entities: int
    total_calls: int
    cross_module_calls: int
    resolved_calls: int
    unresolved_calls: int
    ambiguous_calls: int
    module_relationships: tuple[ModuleRelationship, ...]
    cross_module_call_records: tuple[CrossModuleCall, ...]
    unresolved_references: tuple[UnresolvedCrossModuleReference, ...]

    @property
    def has_cross_module_relationships(self) -> bool:
        return bool(self.module_relationships)

    @property
    def has_unresolved_references(self) -> bool:
        return bool(self.unresolved_references)

    @property
    def resolution_percentage(self) -> float:
        if self.cross_module_calls == 0:
            return 100.0

        return round(
            self.resolved_calls / self.cross_module_calls * 100,
            2,
        )

    @property
    def healthy(self) -> bool:
        return self.unresolved_calls == 0 and self.ambiguous_calls == 0


class CrossModuleRelationshipAnalysisService:
    """Analyze function and method relationships across Python modules."""

    def __init__(
        self,
        call_graph_service: CallGraphService | None = None,
        code_entity_extractor: CodeEntityExtractor | None = None,
    ):
        self.call_graph_service = (
            call_graph_service or CallGraphService()
        )
        self.code_entity_extractor = (
            code_entity_extractor or CodeEntityExtractor()
        )

    def analyze(
        self,
        parsed_sources: Mapping[str, ParsedSource],
    ) -> CrossModuleRelationshipAnalysisResult:
        """Analyze cross-module calls in the supplied parsed sources."""

        self._validate_inputs(parsed_sources)

        calls: list[CallRecord] = []
        entities: list[CodeEntity] = []
        analyzed_files = 0
        skipped_files = 0

        file_to_module: dict[str, str] = {}
        module_to_file: dict[str, str] = {}
        module_stems: dict[str, str] = {}

        for source_key, parsed_source in parsed_sources.items():
            normalized_path = self._normalize_path(source_key)

            if parsed_source.filename != source_key:
                raise CrossModuleRelationshipAnalysisError(
                    f"ParsedSource filename '{parsed_source.filename}' "
                    f"does not match mapping key '{source_key}'."
                )

            if parsed_source.language.lower() != "python":
                skipped_files += 1
                continue

            module_name = self._module_name(normalized_path)
            module_stem = PurePosixPath(normalized_path).stem

            # CallGraphService and CodeEntityExtractor use filename stems
            # for their module identities. Reject duplicate stems to keep
            # the identities consistent across the analysis.
            if module_stem in module_stems:
                raise CrossModuleRelationshipAnalysisError(
                    f"Duplicate module name '{module_stem}' was found "
                    f"in '{module_stems[module_stem]}' and "
                    f"'{normalized_path}'."
                )

            module_stems[module_stem] = normalized_path

            if module_name in module_to_file:
                raise CrossModuleRelationshipAnalysisError(
                    f"Duplicate module name '{module_name}' was found "
                    "in multiple source files."
                )

            try:
                call_result = self.call_graph_service.analyze(
                    parsed_source
                )
                extracted_entities = self.code_entity_extractor.extract(
                    parsed_source
                )
            except (CallGraphError, CodeEntityExtractionError) as exc:
                raise CrossModuleRelationshipAnalysisError(
                    f"Unable to analyze '{source_key}': {exc}"
                ) from exc

            analyzed_files += 1
            calls.extend(call_result.calls)
            entities.extend(extracted_entities)

            file_to_module[normalized_path] = module_name
            module_to_file[module_name] = normalized_path

        entity_index = self._build_entity_index(entities)

        cross_module_records: list[CrossModuleCall] = []
        unresolved_references: list[
            UnresolvedCrossModuleReference
        ] = []

        for call in calls:
            source_path = self._normalize_path(call.filename)
            source_module = file_to_module.get(source_path)

            if source_module is None:
                continue

            resolution = self._resolve_call(
                call=call,
                source_module=source_module,
                entity_index=entity_index,
                module_to_file=module_to_file,
            )

            if resolution is None:
                continue

            cross_module_records.append(resolution)

            if (
                resolution.resolution_status
                != CrossModuleResolutionStatus.RESOLVED
            ):
                unresolved_references.append(
                    UnresolvedCrossModuleReference(
                        source_module=source_module,
                        source_file=source_path,
                        caller=call.caller,
                        callee=call.callee,
                        line=call.line,
                        reason=self._resolution_reason(
                            resolution.resolution_status
                        ),
                    )
                )

        ordered_calls = tuple(
            sorted(
                cross_module_records,
                key=lambda item: (
                    item.source_module,
                    item.source_file,
                    item.line,
                    item.callee,
                    item.target_module or "",
                ),
            )
        )

        ordered_unresolved = tuple(
            sorted(
                unresolved_references,
                key=lambda item: (
                    item.source_module,
                    item.source_file,
                    item.line,
                    item.callee,
                ),
            )
        )

        relationships = self._build_module_relationships(
            ordered_calls
        )

        resolved_count = sum(
            1
            for item in ordered_calls
            if item.resolution_status
            == CrossModuleResolutionStatus.RESOLVED
        )

        ambiguous_count = sum(
            1
            for item in ordered_calls
            if item.resolution_status
            == CrossModuleResolutionStatus.AMBIGUOUS
        )

        unresolved_count = sum(
            1
            for item in ordered_calls
            if item.resolution_status
            == CrossModuleResolutionStatus.UNRESOLVED
        )

        return CrossModuleRelationshipAnalysisResult(
            total_files=len(parsed_sources),
            analyzed_files=analyzed_files,
            skipped_files=skipped_files,
            total_modules=len(module_to_file),
            total_entities=len(entities),
            total_calls=len(calls),
            cross_module_calls=len(ordered_calls),
            resolved_calls=resolved_count,
            unresolved_calls=unresolved_count,
            ambiguous_calls=ambiguous_count,
            module_relationships=relationships,
            cross_module_call_records=ordered_calls,
            unresolved_references=ordered_unresolved,
        )

    def _validate_inputs(
        self,
        parsed_sources: Mapping[str, ParsedSource],
    ) -> None:
        if not isinstance(parsed_sources, Mapping):
            raise CrossModuleRelationshipAnalysisError(
                "parsed_sources must be a mapping."
            )

        for source_key, parsed_source in parsed_sources.items():
            if not isinstance(source_key, str) or not source_key.strip():
                raise CrossModuleRelationshipAnalysisError(
                    "Source file keys must be non-empty strings."
                )

            self._normalize_path(source_key)

            if not isinstance(parsed_source, ParsedSource):
                raise CrossModuleRelationshipAnalysisError(
                    f"Invalid ParsedSource for '{source_key}'."
                )

    @staticmethod
    def _normalize_path(source_path: str) -> str:
        normalized = source_path.replace("\\", "/").strip()

        if (
            not normalized
            or normalized.startswith("/")
            or any(
                part in ("", ".", "..")
                for part in normalized.split("/")
            )
        ):
            raise CrossModuleRelationshipAnalysisError(
                f"Invalid relative source path '{source_path}'."
            )

        return normalized

    @staticmethod
    def _module_name(source_path: str) -> str:
        path = PurePosixPath(source_path)
        module_parts = list(path.with_suffix("").parts)

        if module_parts and module_parts[-1] == "__init__":
            module_parts.pop()

        if not module_parts:
            raise CrossModuleRelationshipAnalysisError(
                f"Cannot determine module name from '{source_path}'."
            )

        return ".".join(module_parts)

    @staticmethod
    def _build_entity_index(
        entities: list[CodeEntity],
    ) -> dict[str, list[CodeEntity]]:
        index: dict[str, list[CodeEntity]] = {}

        for entity in entities:
            if entity.entity_type not in ("function", "method"):
                continue

            index.setdefault(entity.name, []).append(entity)
            index.setdefault(entity.qualified_name, []).append(entity)

        return index

    def _resolve_call(
        self,
        call: CallRecord,
        source_module: str,
        entity_index: dict[str, list[CodeEntity]],
        module_to_file: dict[str, str],
    ) -> CrossModuleCall | None:
        """Resolve a call when it clearly targets another repository module."""

        if call.callee == "<dynamic>":
            return None

        candidates = self._find_candidates(
            call.callee,
            source_module,
            entity_index,
            module_to_file,
        )

        if not candidates:
            possible_module = self._possible_target_module(
                call.callee,
                source_module,
                module_to_file,
            )

            if possible_module is None:
                return None

            return CrossModuleCall(
                source_module=source_module,
                target_module=possible_module,
                source_file=self._normalize_path(call.filename),
                target_file=module_to_file[possible_module],
                caller=call.caller,
                callee=call.callee,
                caller_type=call.caller_type,
                call_type=call.call_type,
                relationship_type=self._relationship_type(call),
                line=call.line,
                resolution_status=CrossModuleResolutionStatus.UNRESOLVED,
                target_entity=None,
            )

        if len(candidates) > 1:
            target_modules = {
                self._entity_module(candidate)
                for candidate in candidates
            }

            target_modules.discard(source_module)

            if not target_modules:
                return None

            if len(target_modules) > 1:
                return CrossModuleCall(
                    source_module=source_module,
                    target_module=None,
                    source_file=self._normalize_path(call.filename),
                    target_file=None,
                    caller=call.caller,
                    callee=call.callee,
                    caller_type=call.caller_type,
                    call_type=call.call_type,
                    relationship_type=self._relationship_type(call),
                    line=call.line,
                    resolution_status=CrossModuleResolutionStatus.AMBIGUOUS,
                    target_entity=None,
                )

            target_module = next(iter(target_modules))
            target_entity = sorted(
                candidates,
                key=lambda item: item.qualified_name,
            )[0]

            return self._create_resolved_record(
                call,
                source_module,
                target_module,
                target_entity,
                module_to_file,
            )

        target_entity = candidates[0]
        target_module = self._entity_module(target_entity)

        if target_module == source_module:
            return None

        return self._create_resolved_record(
            call,
            source_module,
            target_module,
            target_entity,
            module_to_file,
        )

    def _find_candidates(
        self,
        callee: str,
        source_module: str,
        entity_index: dict[str, list[CodeEntity]],
        module_to_file: dict[str, str],
    ) -> list[CodeEntity]:
        """Find possible target entities for a call expression."""

        candidates: list[CodeEntity] = []

        if callee in entity_index:
            candidates.extend(entity_index[callee])

        parts = callee.split(".")

        if len(parts) >= 2:
            target_module = self._resolve_module_prefix(
                parts[:-1],
                module_to_file,
            )

            if target_module and target_module != source_module:
                symbol = parts[-1]

                candidates.extend(
                    entity
                    for entity in entity_index.get(symbol, [])
                    if self._entity_module(entity) == target_module
                )

                qualified_name = f"{target_module}.{symbol}"
                candidates.extend(
                    entity_index.get(qualified_name, [])
                )

        unique: dict[tuple[str, str], CodeEntity] = {}

        for entity in candidates:
            target_module = self._entity_module(entity)

            if target_module == source_module:
                continue

            if target_module not in module_to_file:
                continue

            unique[
                (entity.filename, entity.qualified_name)
            ] = entity

        return sorted(
            unique.values(),
            key=lambda item: (
                item.filename,
                item.qualified_name,
            ),
        )

    @staticmethod
    def _resolve_module_prefix(
        parts: list[str],
        module_to_file: dict[str, str],
    ) -> str | None:
        if not parts:
            return None

        candidate = ".".join(parts)

        if candidate in module_to_file:
            return candidate

        matches = [
            module
            for module in module_to_file
            if module.endswith("." + candidate)
        ]

        if len(matches) == 1:
            return matches[0]

        return None

    @staticmethod
    def _possible_target_module(
        callee: str,
        source_module: str,
        module_to_file: dict[str, str],
    ) -> str | None:
        parts = callee.split(".")

        if len(parts) < 2:
            return None

        prefix = ".".join(parts[:-1])

        if prefix in module_to_file and prefix != source_module:
            return prefix

        matches = [
            module
            for module in module_to_file
            if module.endswith("." + prefix)
            and module != source_module
        ]

        if len(matches) == 1:
            return matches[0]

        return None

    @staticmethod
    def _entity_module(entity: CodeEntity) -> str:
        return CrossModuleRelationshipAnalysisService._module_name(
            entity.filename.replace("\\", "/")
        )

    def _create_resolved_record(
        self,
        call: CallRecord,
        source_module: str,
        target_module: str,
        target_entity: CodeEntity,
        module_to_file: dict[str, str],
    ) -> CrossModuleCall:
        return CrossModuleCall(
            source_module=source_module,
            target_module=target_module,
            source_file=self._normalize_path(call.filename),
            target_file=module_to_file[target_module],
            caller=call.caller,
            callee=call.callee,
            caller_type=call.caller_type,
            call_type=call.call_type,
            relationship_type=self._relationship_type(call),
            line=call.line,
            resolution_status=CrossModuleResolutionStatus.RESOLVED,
            target_entity=target_entity.qualified_name,
        )

    @staticmethod
    def _relationship_type(call: CallRecord) -> str:
        if call.caller_type == "method":
            return CrossModuleRelationshipType.METHOD_CALL

        return CrossModuleRelationshipType.FUNCTION_CALL

    @staticmethod
    def _resolution_reason(status: str) -> str:
        if status == CrossModuleResolutionStatus.AMBIGUOUS:
            return (
                "The call matches multiple target modules and "
                "cannot be resolved uniquely."
            )

        return (
            "A target module was identified, but the referenced "
            "function or method could not be resolved."
        )

    @staticmethod
    def _build_module_relationships(
        calls: tuple[CrossModuleCall, ...],
    ) -> tuple[ModuleRelationship, ...]:
        grouped: dict[
            tuple[str, str],
            list[CrossModuleCall],
        ] = {}

        for call in calls:
            if call.target_module is None:
                continue

            key = (call.source_module, call.target_module)
            grouped.setdefault(key, []).append(call)

        relationships = []

        for (source_module, target_module), records in sorted(
            grouped.items()
        ):
            ordered_records = tuple(
                sorted(
                    records,
                    key=lambda item: (
                        item.source_file,
                        item.line,
                        item.callee,
                    ),
                )
            )

            relationship_types = tuple(
                sorted(
                    {
                        item.relationship_type
                        for item in ordered_records
                    }
                )
            )

            relationships.append(
                ModuleRelationship(
                    source_module=source_module,
                    target_module=target_module,
                    relationship_count=len(ordered_records),
                    relationship_types=relationship_types,
                    calls=ordered_records,
                )
            )

        return tuple(relationships)
