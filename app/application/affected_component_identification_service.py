"""Identify affected repository components from change-impact evidence."""

from dataclasses import dataclass
from enum import Enum
from typing import Iterable


class AffectedComponentIdentificationError(ValueError):
    """Raised when affected-component identification receives invalid input."""


class ComponentImpactLevel(str, Enum):
    DIRECT = "direct"
    INDIRECT = "indirect"


@dataclass(frozen=True)
class AffectedComponentEvidence:
    """Traceable evidence explaining why a component was identified."""

    source: str
    relationship_type: str
    changed_target: str
    reason: str
    line: int = 0
    depth: int = 1

    def __post_init__(self):
        for field_name in ("source", "relationship_type", "changed_target", "reason"):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise AffectedComponentIdentificationError(
                    f"{field_name} must be a non-empty string."
                )
        if isinstance(self.line, bool) or not isinstance(self.line, int) or self.line < 0:
            raise AffectedComponentIdentificationError(
                "line must be a non-negative integer."
            )
        if isinstance(self.depth, bool) or not isinstance(self.depth, int) or self.depth < 1:
            raise AffectedComponentIdentificationError(
                "depth must be a positive integer."
            )


@dataclass(frozen=True)
class AffectedComponent:
    """A repository file or code entity affected by a proposed change."""

    file_path: str
    entity_name: str
    entity_type: str
    impact_level: ComponentImpactLevel
    impact_depth: int
    impact_types: tuple
    changed_targets: tuple
    relationship_types: tuple
    evidence: tuple

    def __post_init__(self):
        for field_name in ("file_path", "entity_name", "entity_type"):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise AffectedComponentIdentificationError(
                    f"{field_name} must be a non-empty string."
                )
        if not isinstance(self.impact_level, ComponentImpactLevel):
            raise AffectedComponentIdentificationError(
                "impact_level must be a ComponentImpactLevel."
            )
        if isinstance(self.impact_depth, bool) or not isinstance(self.impact_depth, int) or self.impact_depth < 0:
            raise AffectedComponentIdentificationError(
                "impact_depth must be a non-negative integer."
            )
        for field_name in (
            "impact_types", "changed_targets", "relationship_types", "evidence"
        ):
            value = getattr(self, field_name)
            if not isinstance(value, tuple):
                raise AffectedComponentIdentificationError(
                    f"{field_name} must be a tuple."
                )


@dataclass(frozen=True)
class AffectedComponentIdentificationResult:
    """Summary and detailed inventory of affected repository components."""

    total_components: int
    total_affected_files: int
    direct_components: int
    indirect_components: int
    components: tuple
    affected_files: tuple
    unmapped_findings: tuple
    data_flow_files_considered: int = 0
    data_flow_edges_considered: int = 0

    def __post_init__(self):
        for field_name in (
            "total_components", "total_affected_files", "direct_components",
            "indirect_components", "data_flow_files_considered",
            "data_flow_edges_considered",
        ):
            value = getattr(self, field_name)
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise AffectedComponentIdentificationError(
                    f"{field_name} must be a non-negative integer."
                )
        for field_name in ("components", "affected_files", "unmapped_findings"):
            if not isinstance(getattr(self, field_name), tuple):
                raise AffectedComponentIdentificationError(
                    f"{field_name} must be a tuple."
                )
        if self.total_components != len(self.components):
            raise AffectedComponentIdentificationError(
                "total_components must match the components collection."
            )
        if self.total_affected_files != len(self.affected_files):
            raise AffectedComponentIdentificationError(
                "total_affected_files must match the affected_files collection."
            )
        if self.direct_components + self.indirect_components != self.total_components:
            raise AffectedComponentIdentificationError(
                "Direct and indirect component counts must match total_components."
            )

    @property
    def has_affected_components(self):
        return bool(self.components)

    @property
    def healthy(self):
        return not self.unmapped_findings

    @property
    def directly_affected_components(self):
        return tuple(
            item for item in self.components
            if item.impact_level is ComponentImpactLevel.DIRECT
        )

    @property
    def indirectly_affected_components(self):
        return tuple(
            item for item in self.components
            if item.impact_level is ComponentImpactLevel.INDIRECT
        )

    @property
    def direct_impact_count(self):
        return self.direct_components

    @property
    def indirect_impact_count(self):
        return self.indirect_components


class AffectedComponentIdentificationService:
    """Consolidate impact findings into an entity-level affected-component inventory.

    The service accepts the result objects produced by the preceding Phase 4.5
    components. It intentionally uses their documented attributes rather than
    importing their implementations, keeping this application service loosely
    coupled to the analysis services.
    """

    def identify(
        self,
        changed_files=(),
        changed_entities=(),
        code_entities=(),
        change_impact_result=None,
        impact_analysis_result=None,
        data_flow_results=(),
    ):
        changed_files = self._string_collection(changed_files, "changed_files")
        changed_entities = self._string_collection(
            changed_entities, "changed_entities"
        )
        code_entities = self._object_collection(code_entities, "code_entities")
        data_flow_results = self._object_collection(
            data_flow_results, "data_flow_results"
        )

        self._validate_optional_result(
            change_impact_result, "change_impact_result", "findings"
        )
        self._validate_optional_result(
            impact_analysis_result, "impact_analysis_result", "findings"
        )

        records = {}

        for changed_file in changed_files:
            self._add_component(
                records,
                file_path=changed_file,
                entity=None,
                level=ComponentImpactLevel.DIRECT,
                depth=0,
                impact_type="changed_file",
                changed_target=changed_file,
                relationship_type="change",
                source="changed_files",
                reason="The file was explicitly marked as changed.",
                line=0,
                code_entities=code_entities,
            )

        for changed_entity in changed_entities:
            entity = self._find_entity(changed_entity, code_entities)
            if entity is None:
                self._add_unmapped(
                    records, f"Changed entity could not be mapped: {changed_entity}"
                )
                continue
            self._add_component(
                records,
                file_path=entity.filename,
                entity=entity,
                level=ComponentImpactLevel.DIRECT,
                depth=0,
                impact_type="changed_entity",
                changed_target=changed_entity,
                relationship_type="change",
                source="changed_entities",
                reason="The code entity was explicitly marked as changed.",
                line=entity.line,
                code_entities=code_entities,
            )

        if change_impact_result is not None:
            for finding in change_impact_result.findings:
                self._consume_change_finding(records, finding, code_entities)

        if impact_analysis_result is not None:
            for finding in impact_analysis_result.findings:
                self._consume_indirect_finding(records, finding, code_entities)

        unmapped = tuple(sorted(records.pop("__unmapped__", set())))
        components = tuple(
            self._freeze_component(key, value)
            for key, value in sorted(records.items())
        )
        affected_files = tuple(sorted({item.file_path for item in components}))
        direct_count = sum(
            item.impact_level is ComponentImpactLevel.DIRECT for item in components
        )
        indirect_count = len(components) - direct_count

        flow_files = sum(
            1 for result in data_flow_results
            if getattr(result, "analyzed", False) is True
        )
        flow_edges = sum(
            len(getattr(result, "edges", ()))
            for result in data_flow_results
            if getattr(result, "analyzed", False) is True
        )

        return AffectedComponentIdentificationResult(
            total_components=len(components),
            total_affected_files=len(affected_files),
            direct_components=direct_count,
            indirect_components=indirect_count,
            components=components,
            affected_files=affected_files,
            unmapped_findings=unmapped,
            data_flow_files_considered=flow_files,
            data_flow_edges_considered=flow_edges,
        )

    def _consume_change_finding(self, records, finding, code_entities):
        required = ("affected_file", "relationship_type", "changed_target")
        self._require_attributes(finding, required, "change-impact finding")
        file_path = finding.affected_file
        if not isinstance(file_path, str) or not file_path.strip():
            self._add_unmapped(records, "Change-impact finding has no affected_file.")
            return
        entity_ref = getattr(finding, "affected_entity", None)
        entity = self._find_entity(entity_ref, code_entities) if entity_ref else None
        self._add_component(
            records,
            file_path=file_path,
            entity=entity,
            level=ComponentImpactLevel.DIRECT,
            depth=1,
            impact_type=str(finding.relationship_type),
            changed_target=str(finding.changed_target),
            relationship_type=str(finding.relationship_type),
            source="change_impact",
            reason=str(getattr(finding, "reason", "Direct change-impact relationship.")),
            line=self._safe_line(getattr(finding, "line", 0)),
            code_entities=code_entities,
            entity_reference=entity_ref,
        )

    def _consume_indirect_finding(self, records, finding, code_entities):
        required = ("affected_file", "impact_type", "changed_target", "depth")
        self._require_attributes(finding, required, "direct/indirect impact finding")
        file_path = finding.affected_file
        if not isinstance(file_path, str) or not file_path.strip():
            self._add_unmapped(records, "Impact finding has no affected_file.")
            return
        depth = finding.depth
        if isinstance(depth, bool) or not isinstance(depth, int) or depth < 1:
            self._add_unmapped(records, "Impact finding has an invalid depth.")
            return
        entity_ref = getattr(finding, "affected_entity", None)
        entity = self._find_entity(entity_ref, code_entities) if entity_ref else None
        level = (
            ComponentImpactLevel.DIRECT
            if depth == 1
            else ComponentImpactLevel.INDIRECT
        )
        relationship_types = getattr(finding, "relationship_types", ())
        if not isinstance(relationship_types, (tuple, list)):
            relationship_types = ()
        if relationship_types:
            relation = " -> ".join(str(item) for item in relationship_types)
        else:
            relation = str(getattr(finding, "impact_type", "impact"))
        self._add_component(
            records,
            file_path=file_path,
            entity=entity,
            level=level,
            depth=depth,
            impact_type=str(finding.impact_type),
            changed_target=str(finding.changed_target),
            relationship_type=relation,
            source="direct_indirect_impact",
            reason=str(getattr(finding, "reason", "Dependency or call-graph impact path.")),
            line=self._safe_line(getattr(finding, "line", 0)),
            code_entities=code_entities,
            entity_reference=entity_ref,
        )

    def _add_component(
        self, records, file_path, entity, level, depth, impact_type,
        changed_target, relationship_type, source, reason, line,
        code_entities, entity_reference=None,
    ):
        if entity is None and entity_reference:
            entity = self._find_entity(entity_reference, code_entities)
        if entity is None:
            entity = self._find_file_entity(file_path, code_entities)

        if entity is not None:
            name = entity.qualified_name
            entity_type = entity.entity_type
            file_path = entity.filename
        else:
            name = file_path
            entity_type = "file"

        key = (file_path, name, entity_type)
        record = records.setdefault(
            key,
            {
                "level": level,
                "depth": depth,
                "impact_types": set(),
                "changed_targets": set(),
                "relationship_types": set(),
                "evidence": set(),
            },
        )
        if level is ComponentImpactLevel.DIRECT:
            record["level"] = ComponentImpactLevel.DIRECT
        record["depth"] = min(record["depth"], depth)
        record["impact_types"].add(impact_type)
        record["changed_targets"].add(changed_target)
        record["relationship_types"].add(relationship_type)
        record["evidence"].add(
            AffectedComponentEvidence(
                source=source,
                relationship_type=relationship_type or "impact",
                changed_target=changed_target or "unknown",
                reason=reason or "Impact identified.",
                line=line,
                depth=max(1, depth),
            )
        )

    @staticmethod
    def _freeze_component(key, record):
        file_path, name, entity_type = key
        return AffectedComponent(
            file_path=file_path,
            entity_name=name,
            entity_type=entity_type,
            impact_level=record["level"],
            impact_depth=record["depth"],
            impact_types=tuple(sorted(record["impact_types"])),
            changed_targets=tuple(sorted(record["changed_targets"])),
            relationship_types=tuple(sorted(record["relationship_types"])),
            evidence=tuple(
                sorted(
                    record["evidence"],
                    key=lambda item: (
                        item.source, item.line, item.relationship_type,
                        item.changed_target, item.reason,
                    ),
                )
            ),
        )

    @staticmethod
    def _find_entity(reference, code_entities):
        if not isinstance(reference, str) or not reference.strip():
            return None
        normalized = reference.strip().replace("\\", "/")
        candidates = []
        for entity in code_entities:
            names = {
                getattr(entity, "name", None),
                getattr(entity, "qualified_name", None),
            }
            if normalized in names:
                candidates.append(entity)
        if len(candidates) == 1:
            return candidates[0]
        if len(candidates) > 1:
            return sorted(
                candidates,
                key=lambda item: (item.filename, item.qualified_name),
            )[0]
        short_name = normalized.rsplit(".", 1)[-1]
        candidates = [
            entity for entity in code_entities
            if getattr(entity, "name", None) == short_name
        ]
        if len(candidates) == 1:
            return candidates[0]
        return None

    @staticmethod
    def _find_file_entity(file_path, code_entities):
        candidates = [
            entity for entity in code_entities
            if getattr(entity, "filename", None) == file_path
            and getattr(entity, "entity_type", None) == "module"
        ]
        return candidates[0] if candidates else None

    @staticmethod
    def _require_attributes(value, attributes, label):
        if any(not hasattr(value, attribute) for attribute in attributes):
            raise AffectedComponentIdentificationError(
                f"{label} is missing required attributes."
            )

    @staticmethod
    def _validate_optional_result(value, label, attribute):
        if value is not None and not hasattr(value, attribute):
            raise AffectedComponentIdentificationError(
                f"{label} must expose a {attribute} collection."
            )
        if value is not None and not isinstance(getattr(value, attribute), (tuple, list)):
            raise AffectedComponentIdentificationError(
                f"{label}.{attribute} must be an ordered collection."
            )

    @staticmethod
    def _string_collection(values, label):
        if values is None or isinstance(values, (str, bytes, dict, set, frozenset)):
            raise AffectedComponentIdentificationError(
                f"{label} must be an ordered iterable of non-empty strings."
            )
        try:
            result = tuple(values)
        except TypeError as exc:
            raise AffectedComponentIdentificationError(
                f"{label} must be iterable."
            ) from exc
        if any(not isinstance(item, str) or not item.strip() for item in result):
            raise AffectedComponentIdentificationError(
                f"{label} must contain only non-empty strings."
            )
        if len(result) != len(set(result)):
            raise AffectedComponentIdentificationError(
                f"{label} must not contain duplicates."
            )
        return result

    @staticmethod
    def _object_collection(values, label):
        if values is None or isinstance(values, (str, bytes, dict, set, frozenset)):
            raise AffectedComponentIdentificationError(
                f"{label} must be an ordered iterable."
            )
        try:
            return tuple(values)
        except TypeError as exc:
            raise AffectedComponentIdentificationError(
                f"{label} must be iterable."
            ) from exc

    @staticmethod
    def _safe_line(value):
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            return 0
        return value

    @staticmethod
    def _add_unmapped(records, message):
        records.setdefault("__unmapped__", set()).add(message)
