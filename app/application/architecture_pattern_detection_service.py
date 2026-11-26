
"""Heuristic architecture-pattern detection for repository intelligence."""

from dataclasses import dataclass
from enum import Enum


class ArchitecturePatternDetectionError(ValueError):
    """Invalid input or model data."""


class ArchitecturePattern(str, Enum):
    LAYERED = "layered_architecture"
    MVC = "model_view_controller"
    REPOSITORY = "repository_pattern"
    SERVICE_LAYER = "service_layer"
    FACTORY = "factory_pattern"
    AGENT = "agent_architecture"


class PatternConfidence(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass(frozen=True)
class ArchitecturePatternEvidence:
    source: str
    description: str
    file_path: str = ""
    entity_name: str = ""

    def __post_init__(self):
        for field in ("source", "description"):
            value = getattr(self, field)
            if not isinstance(value, str) or not value.strip():
                raise ArchitecturePatternDetectionError(
                    f"{field} must be a non-empty string."
                )

        for field in ("file_path", "entity_name"):
            if not isinstance(getattr(self, field), str):
                raise ArchitecturePatternDetectionError(
                    f"{field} must be a string."
                )


@dataclass(frozen=True)
class ArchitecturePatternFinding:
    pattern: ArchitecturePattern
    confidence: PatternConfidence
    evidence_count: int
    evidence: tuple
    affected_files: tuple
    description: str

    def __post_init__(self):
        if not isinstance(self.pattern, ArchitecturePattern):
            raise ArchitecturePatternDetectionError(
                "pattern must be an ArchitecturePattern."
            )

        if not isinstance(self.confidence, PatternConfidence):
            raise ArchitecturePatternDetectionError(
                "confidence must be a PatternConfidence."
            )

        if (
            isinstance(self.evidence_count, bool)
            or not isinstance(self.evidence_count, int)
            or self.evidence_count < 1
        ):
            raise ArchitecturePatternDetectionError(
                "evidence_count must be a positive integer."
            )

        if (
            not isinstance(self.evidence, tuple)
            or len(self.evidence) != self.evidence_count
        ):
            raise ArchitecturePatternDetectionError(
                "evidence_count must match a non-empty evidence tuple."
            )

        if not isinstance(self.affected_files, tuple):
            raise ArchitecturePatternDetectionError(
                "affected_files must be a tuple."
            )

        if not isinstance(self.description, str) or not self.description.strip():
            raise ArchitecturePatternDetectionError(
                "description must be a non-empty string."
            )


@dataclass(frozen=True)
class ArchitecturePatternDetectionResult:
    total_files: int
    total_entities: int
    total_dependencies: int
    patterns_detected: int
    findings: tuple
    analyzed_files: tuple
    skipped_inputs: tuple = ()

    def __post_init__(self):
        for field in (
            "total_files",
            "total_entities",
            "total_dependencies",
            "patterns_detected",
        ):
            value = getattr(self, field)

            if (
                isinstance(value, bool)
                or not isinstance(value, int)
                or value < 0
            ):
                raise ArchitecturePatternDetectionError(
                    f"{field} must be a non-negative integer."
                )

        for field in ("findings", "analyzed_files", "skipped_inputs"):
            if not isinstance(getattr(self, field), tuple):
                raise ArchitecturePatternDetectionError(
                    f"{field} must be a tuple."
                )

        if self.patterns_detected != len(self.findings):
            raise ArchitecturePatternDetectionError(
                "patterns_detected must match findings."
            )

    @property
    def has_patterns(self):
        return bool(self.findings)

    @property
    def healthy(self):
        return not self.skipped_inputs

    @property
    def detected_patterns(self):
        return tuple(item.pattern for item in self.findings)

    @property
    def high_confidence_findings(self):
        return tuple(
            item
            for item in self.findings
            if item.confidence is PatternConfidence.HIGH
        )

    def get_pattern(self, pattern):
        if isinstance(pattern, str):
            try:
                pattern = ArchitecturePattern(pattern)
            except ValueError:
                return None

        return next(
            (
                item
                for item in self.findings
                if item.pattern is pattern
            ),
            None,
        )


class ArchitecturePatternDetectionService:
    """Detect structural indicators; findings are heuristic, evidence-backed signals."""

    LAYERS = {
        "presentation": {
            "presentation", "ui", "views", "view",
            "controllers", "controller", "pages", "api",
        },
        "application": {
            "application", "services", "service",
            "use_cases", "usecases",
        },
        "domain": {
            "domain", "entities", "entity", "models", "model",
        },
        "infrastructure": {
            "infrastructure", "repositories", "repository",
            "adapters", "persistence",
        },
    }

    def analyze(
        self,
        source_files=(),
        code_entities=(),
        dependencies=(),
        call_graphs=(),
    ):
        files = self._strings(source_files, "source_files")
        entities = self._objects(code_entities, "code_entities")
        dependencies = self._objects(dependencies, "dependencies")
        call_graphs = self._objects(call_graphs, "call_graphs")

        entity_data = self._entities(entities)
        dependency_data = self._dependencies(dependencies)
        call_data = self._calls(call_graphs)

        all_files = {self._path(item) for item in files}

        all_files.update(
            item["filename"] for item in entity_data
        )

        all_files.update(
            item["source_file"] for item in dependency_data
        )

        all_files.update(
            item["filename"] for item in call_data
        )

        all_files = tuple(sorted(all_files))

        findings = []

        findings += self._layered(all_files)
        findings += self._mvc(entity_data)

        findings += self._named_pattern(
            ArchitecturePattern.REPOSITORY,
            entity_data,
            lambda item: (
                item["entity_type"] == "class"
                and (
                    item["name"].lower().endswith("repository")
                    or "repository" in self._parts(item["filename"])
                )
            ),
            "Repository-like classes suggest a data-access abstraction.",
            "Found repository-like class",
            PatternConfidence.MEDIUM,
            PatternConfidence.HIGH,
        )

        service_items = [
            item
            for item in entity_data
            if (
                item["entity_type"] == "class"
                and (
                    item["name"].lower().endswith("service")
                    or bool(
                        {"service", "services"}
                        & set(self._parts(item["filename"])[:-1])
                    )
                )
            )
        ]

        service_files = {
            path
            for path in all_files
            if (
                set(self._parts(path)[:-1])
                & {"service", "services"}
            )
        }

        known_service_files = {
            item["filename"] for item in service_items
        }

        for path in sorted(service_files - known_service_files):
            service_items.append({
                "name": path,
                "qualified_name": path,
                "filename": path,
                "entity_type": "file",
            })

        findings += self._from_items(
            ArchitecturePattern.SERVICE_LAYER,
            service_items,
            "Service classes or modules indicate a service layer.",
            "Found service-like component",
            PatternConfidence.MEDIUM,
            PatternConfidence.HIGH,
        )

        findings += self._named_pattern(
            ArchitecturePattern.FACTORY,
            entity_data,
            lambda item: (
                item["name"].lower().endswith("factory")
                or item["qualified_name"].lower().split(".")[-1].startswith(
                    "create_"
                )
            ),
            "Factory-like entities may encapsulate object construction.",
            "Found factory-like entity",
            PatternConfidence.MEDIUM,
            PatternConfidence.MEDIUM,
        )

        agent_items = [
            item
            for item in entity_data
            if (
                item["name"].lower().endswith("agent")
                or "agents" in self._parts(item["filename"])[:-1]
            )
        ]

        if agent_items:
            evidence = self._item_evidence(
                agent_items,
                "entity_name_and_location",
                "Found agent-like component",
            )

            agent_files = {
                item["filename"] for item in agent_items
            }

            connected = [
                item
                for item in call_data
                if (
                    item["filename"] in agent_files
                    and item["total_calls"] > 0
                )
            ]

            evidence.extend(
                ArchitecturePatternEvidence(
                    "call_graph",
                    (
                        f"Agent file has {item['total_calls']} "
                        "call relationship(s)."
                    ),
                    item["filename"],
                )
                for item in connected
            )

            findings.append(
                self._finding(
                    ArchitecturePattern.AGENT,
                    evidence,
                    (
                        "Agent-like components are present; naming and "
                        "call structure do not prove autonomous behavior."
                    ),
                    agent_files,
                    (
                        PatternConfidence.HIGH
                        if connected
                        else PatternConfidence.MEDIUM
                    ),
                )
            )

        findings = tuple(
            sorted(findings, key=lambda item: item.pattern.value)
        )

        return ArchitecturePatternDetectionResult(
            total_files=len(all_files),
            total_entities=len(entity_data),
            total_dependencies=len(dependency_data),
            patterns_detected=len(findings),
            findings=findings,
            analyzed_files=all_files,
        )

    def _layered(self, files):
        groups = {}

        for path in files:
            parts = self._parts(path)

            for layer, aliases in self.LAYERS.items():
                if set(parts[:-1]) & aliases:
                    groups.setdefault(layer, set()).add(path)

        if len(groups) < 3:
            return []

        evidence = [
            ArchitecturePatternEvidence(
                "repository_structure",
                f"Found {len(paths)} file(s) in the {layer} layer.",
                sorted(paths)[0],
            )
            for layer, paths in sorted(groups.items())
        ]

        confidence = (
            PatternConfidence.HIGH
            if len(groups) == 4
            else PatternConfidence.MEDIUM
        )

        return [
            self._finding(
                ArchitecturePattern.LAYERED,
                evidence,
                "Three or more distinct architectural layers are represented.",
                set().union(*groups.values()),
                confidence,
            )
        ]

    def _mvc(self, entities):
        groups = {
            "model": set(),
            "view": set(),
            "controller": set(),
        }

        for item in entities:
            if item["entity_type"] not in {"class", "module"}:
                continue

            name = item["name"].lower()
            parts = self._parts(item["filename"])

            if "model" in parts or name.endswith("model"):
                groups["model"].add(item["filename"])

            if "view" in parts or name.endswith("view"):
                groups["view"].add(item["filename"])

            if "controller" in parts or name.endswith("controller"):
                groups["controller"].add(item["filename"])

        if any(not values for values in groups.values()):
            return []

        evidence = [
            ArchitecturePatternEvidence(
                "code_entity_and_path",
                f"Identified {kind} component(s).",
                sorted(groups[kind])[0],
            )
            for kind in ("model", "view", "controller")
        ]

        return [
            self._finding(
                ArchitecturePattern.MVC,
                evidence,
                "Model, view, and controller responsibilities are represented.",
                set().union(*groups.values()),
                PatternConfidence.HIGH,
            )
        ]

    def _named_pattern(
        self,
        pattern,
        entities,
        predicate,
        description,
        prefix,
        one_confidence,
        many_confidence,
    ):
        matches = [
            item for item in entities if predicate(item)
        ]

        return self._from_items(
            pattern,
            matches,
            description,
            prefix,
            one_confidence,
            many_confidence,
        )

    def _from_items(
        self,
        pattern,
        items,
        description,
        prefix,
        one_confidence,
        many_confidence,
    ):
        if not items:
            return []

        evidence = self._item_evidence(
            items,
            "entity_name_and_location",
            prefix,
        )

        return [
            self._finding(
                pattern,
                evidence,
                description,
                {item["filename"] for item in items},
                (
                    many_confidence
                    if len(items) >= 2
                    else one_confidence
                ),
            )
        ]

    @staticmethod
    def _item_evidence(items, source, prefix):
        return [
            ArchitecturePatternEvidence(
                source,
                f"{prefix} '{item['qualified_name']}'.",
                item["filename"],
                item["qualified_name"],
            )
            for item in items
        ]

    @staticmethod
    def _finding(
        pattern,
        evidence,
        description,
        files,
        confidence,
    ):
        evidence = tuple(
            sorted(
                set(evidence),
                key=lambda item: (
                    item.source,
                    item.file_path,
                    item.entity_name,
                    item.description,
                ),
            )
        )

        return ArchitecturePatternFinding(
            pattern=pattern,
            confidence=confidence,
            evidence_count=len(evidence),
            evidence=evidence,
            affected_files=tuple(sorted(files)),
            description=description,
        )

    @staticmethod
    def _entities(entities):
        result = []

        for item in entities:
            fields = (
                "name",
                "entity_type",
                "qualified_name",
                "filename",
            )

            if any(not hasattr(item, field) for field in fields):
                raise ArchitecturePatternDetectionError(
                    "Each code entity must expose name, entity_type, "
                    "qualified_name, and filename."
                )

            values = {
                field: getattr(item, field)
                for field in fields
            }

            if any(
                not isinstance(value, str) or not value.strip()
                for value in values.values()
            ):
                raise ArchitecturePatternDetectionError(
                    "Code entity fields must be non-empty strings."
                )

            result.append({
                **values,
                "entity_type": values["entity_type"].lower(),
                "filename": ArchitecturePatternDetectionService._path(
                    values["filename"]
                ),
            })

        return tuple(result)

    @staticmethod
    def _dependencies(dependencies):
        result = []

        for item in dependencies:
            if (
                not hasattr(item, "source_file")
                or not hasattr(item, "imported_module")
            ):
                raise ArchitecturePatternDetectionError(
                    "Each dependency must expose source_file and imported_module."
                )

            source = item.source_file
            module = item.imported_module

            if not isinstance(source, str) or not source.strip():
                raise ArchitecturePatternDetectionError(
                    "Dependency source_file must be non-empty."
                )

            if module is not None and not isinstance(module, str):
                raise ArchitecturePatternDetectionError(
                    "Dependency imported_module must be a string or None."
                )

            result.append({
                "source_file": ArchitecturePatternDetectionService._path(
                    source
                )
            })

        return tuple(result)

    @staticmethod
    def _calls(call_graphs):
        result = []

        for item in call_graphs:
            if (
                not hasattr(item, "filename")
                or not hasattr(item, "total_calls")
            ):
                raise ArchitecturePatternDetectionError(
                    "Each call graph must expose filename and total_calls."
                )

            filename = item.filename
            count = item.total_calls

            if not isinstance(filename, str) or not filename.strip():
                raise ArchitecturePatternDetectionError(
                    "Call graph filename must be non-empty."
                )

            if (
                isinstance(count, bool)
                or not isinstance(count, int)
                or count < 0
            ):
                raise ArchitecturePatternDetectionError(
                    "Call graph total_calls must be a non-negative integer."
                )

            result.append({
                "filename": ArchitecturePatternDetectionService._path(
                    filename
                ),
                "total_calls": count,
            })

        return tuple(result)

    @staticmethod
    def _strings(values, label):
        if values is None or isinstance(
            values,
            (str, bytes, dict, set, frozenset),
        ):
            raise ArchitecturePatternDetectionError(
                f"{label} must be an ordered iterable."
            )

        try:
            result = tuple(values)
        except TypeError as exc:
            raise ArchitecturePatternDetectionError(
                f"{label} must be iterable."
            ) from exc

        if any(
            not isinstance(item, str) or not item.strip()
            for item in result
        ):
            raise ArchitecturePatternDetectionError(
                f"{label} must contain non-empty strings."
            )

        if len(result) != len(set(result)):
            raise ArchitecturePatternDetectionError(
                f"{label} must not contain duplicates."
            )

        return result

    @staticmethod
    def _objects(values, label):
        if values is None or isinstance(
            values,
            (str, bytes, dict, set, frozenset),
        ):
            raise ArchitecturePatternDetectionError(
                f"{label} must be an ordered iterable."
            )

        try:
            return tuple(values)
        except TypeError as exc:
            raise ArchitecturePatternDetectionError(
                f"{label} must be iterable."
            ) from exc

    @staticmethod
    def _path(value):
        value = value.replace("\\", "/").strip()

        while value.startswith("./"):
            value = value[2:]

        return value.rstrip("/")

    @staticmethod
    def _parts(path):
        return tuple(
            part.lower()
            for part in path.split("/")
            if part
        )
