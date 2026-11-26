
"""Module responsibility analysis for repository intelligence."""

import re
from dataclasses import dataclass
from enum import Enum


class ModuleResponsibilityAnalysisError(ValueError):
    """Raised when module responsibility analysis input is invalid."""


class ModuleResponsibility(str, Enum):
    API = "api"
    PRESENTATION = "presentation"
    APPLICATION = "application"
    DOMAIN = "domain"
    INFRASTRUCTURE = "infrastructure"
    DATA_ACCESS = "data_access"
    CONFIGURATION = "configuration"
    TESTING = "testing"
    UTILITIES = "utilities"
    AGENT = "agent"
    SERVICE = "service"
    UNKNOWN = "unknown"


class ResponsibilityConfidence(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass(frozen=True)
class ModuleResponsibilityEvidence:
    source: str
    description: str
    file_path: str = ""
    entity_name: str = ""

    def __post_init__(self):
        if not isinstance(self.source, str) or not self.source.strip():
            raise ModuleResponsibilityAnalysisError(
                "Evidence source must be a non-empty string."
            )

        if not isinstance(self.description, str) or not self.description.strip():
            raise ModuleResponsibilityAnalysisError(
                "Evidence description must be a non-empty string."
            )

        if not isinstance(self.file_path, str):
            raise ModuleResponsibilityAnalysisError(
                "Evidence file_path must be a string."
            )

        if not isinstance(self.entity_name, str):
            raise ModuleResponsibilityAnalysisError(
                "Evidence entity_name must be a string."
            )


@dataclass(frozen=True)
class ModuleResponsibilityFinding:
    module_name: str
    file_path: str
    responsibility: ModuleResponsibility
    confidence: ResponsibilityConfidence
    evidence_count: int
    evidence: tuple
    entity_count: int
    dependency_count: int
    call_count: int
    description: str

    def __post_init__(self):
        if not isinstance(self.module_name, str) or not self.module_name.strip():
            raise ModuleResponsibilityAnalysisError(
                "module_name must be a non-empty string."
            )

        if not isinstance(self.file_path, str) or not self.file_path.strip():
            raise ModuleResponsibilityAnalysisError(
                "file_path must be a non-empty string."
            )

        if not isinstance(self.responsibility, ModuleResponsibility):
            raise ModuleResponsibilityAnalysisError(
                "responsibility must be a ModuleResponsibility."
            )

        if not isinstance(self.confidence, ResponsibilityConfidence):
            raise ModuleResponsibilityAnalysisError(
                "confidence must be a ResponsibilityConfidence."
            )

        if (
            isinstance(self.evidence_count, bool)
            or not isinstance(self.evidence_count, int)
            or self.evidence_count < 1
        ):
            raise ModuleResponsibilityAnalysisError(
                "evidence_count must be a positive integer."
            )

        if (
            not isinstance(self.evidence, tuple)
            or len(self.evidence) != self.evidence_count
            or not all(
                isinstance(item, ModuleResponsibilityEvidence)
                for item in self.evidence
            )
        ):
            raise ModuleResponsibilityAnalysisError(
                "evidence must be a tuple matching evidence_count."
            )

        for field in ("entity_count", "dependency_count", "call_count"):
            value = getattr(self, field)
            if (
                isinstance(value, bool)
                or not isinstance(value, int)
                or value < 0
            ):
                raise ModuleResponsibilityAnalysisError(
                    f"{field} must be a non-negative integer."
                )

        if not isinstance(self.description, str) or not self.description.strip():
            raise ModuleResponsibilityAnalysisError(
                "description must be a non-empty string."
            )


@dataclass(frozen=True)
class ModuleResponsibilityAnalysisResult:
    total_modules: int
    classified_modules: int
    unclassified_modules: int
    findings: tuple
    unclassified_files: tuple
    total_entities: int
    total_dependencies: int
    total_calls: int

    def __post_init__(self):
        for field in (
            "total_modules",
            "classified_modules",
            "unclassified_modules",
            "total_entities",
            "total_dependencies",
            "total_calls",
        ):
            value = getattr(self, field)
            if (
                isinstance(value, bool)
                or not isinstance(value, int)
                or value < 0
            ):
                raise ModuleResponsibilityAnalysisError(
                    f"{field} must be a non-negative integer."
                )

        if not isinstance(self.findings, tuple):
            raise ModuleResponsibilityAnalysisError(
                "findings must be a tuple."
            )

        if not isinstance(self.unclassified_files, tuple):
            raise ModuleResponsibilityAnalysisError(
                "unclassified_files must be a tuple."
            )

        if self.classified_modules != len(self.findings):
            raise ModuleResponsibilityAnalysisError(
                "classified_modules must match findings."
            )

        if self.unclassified_modules != len(self.unclassified_files):
            raise ModuleResponsibilityAnalysisError(
                "unclassified_modules must match unclassified_files."
            )

        if self.total_modules != (
            self.classified_modules + self.unclassified_modules
        ):
            raise ModuleResponsibilityAnalysisError(
                "Module totals are inconsistent."
            )

    @property
    def is_complete(self):
        return self.unclassified_modules == 0

    @property
    def has_unclassified_modules(self):
        return self.unclassified_modules > 0

    @property
    def healthy(self):
        return self.is_complete

    @property
    def high_confidence_findings(self):
        return tuple(
            item
            for item in self.findings
            if item.confidence is ResponsibilityConfidence.HIGH
        )

    @property
    def responsibilities(self):
        return tuple(
            sorted(
                {item.responsibility for item in self.findings},
                key=lambda item: item.value,
            )
        )

    def get_module(self, file_path):
        normalized = ModuleResponsibilityAnalysisService._normalize_path(
            file_path
        )
        return next(
            (
                item
                for item in self.findings
                if item.file_path == normalized
            ),
            None,
        )

    def get_by_responsibility(self, responsibility):
        if isinstance(responsibility, str):
            try:
                responsibility = ModuleResponsibility(responsibility)
            except ValueError:
                return ()

        return tuple(
            item
            for item in self.findings
            if item.responsibility is responsibility
        )


class ModuleResponsibilityAnalysisService:
    """Classifies repository modules using structural and relationship evidence."""

    DIRECTORY_RULES = {
        ModuleResponsibility.API: {
            "api", "apis", "routes", "routers", "endpoints",
        },
        ModuleResponsibility.PRESENTATION: {
            "ui", "views", "view", "pages", "presentation",
            "templates", "components",
        },
        ModuleResponsibility.APPLICATION: {
            "application", "use_cases", "usecases",
        },
        ModuleResponsibility.DOMAIN: {
            "domain", "entities", "entity", "models", "model",
        },
        ModuleResponsibility.INFRASTRUCTURE: {
            "infrastructure", "adapters", "integrations",
            "external", "persistence",
        },
        ModuleResponsibility.DATA_ACCESS: {
            "repositories", "repository", "dao", "database",
            "db", "storage", "data_access",
        },
        ModuleResponsibility.CONFIGURATION: {
            "config", "configuration", "settings",
        },
        ModuleResponsibility.TESTING: {
            "tests", "test", "testing",
        },
        ModuleResponsibility.UTILITIES: {
            "utils", "utilities", "helpers",
        },
        ModuleResponsibility.AGENT: {
            "agents", "agent",
        },
        ModuleResponsibility.SERVICE: {
            "services", "service",
        },
    }

    NAME_RULES = {
        ModuleResponsibility.API: (
            "router", "endpoint", "route", "controller",
        ),
        ModuleResponsibility.PRESENTATION: (
            "view", "page", "component", "screen",
        ),
        ModuleResponsibility.APPLICATION: (
            "use", "case", "usecase", "orchestrator",
        ),
        ModuleResponsibility.DOMAIN: (
            "entity", "model", "schema", "domain",
        ),
        ModuleResponsibility.INFRASTRUCTURE: (
            "adapter", "client", "integration",
        ),
        ModuleResponsibility.DATA_ACCESS: (
            "repository", "dao", "storage", "database",
        ),
        ModuleResponsibility.CONFIGURATION: (
            "config", "settings",
        ),
        ModuleResponsibility.TESTING: (
            "test", "tests",
        ),
        ModuleResponsibility.UTILITIES: (
            "utils", "utilities", "helpers",
        ),
        ModuleResponsibility.AGENT: (
            "agent",
        ),
        ModuleResponsibility.SERVICE: (
            "service",
        ),
    }

    DESCRIPTIONS = {
        ModuleResponsibility.API: "Handles API routes, endpoints, or request controllers.",
        ModuleResponsibility.PRESENTATION: "Handles presentation and user-interface responsibilities.",
        ModuleResponsibility.APPLICATION: "Coordinates application use cases and workflows.",
        ModuleResponsibility.DOMAIN: "Contains domain models, entities, and business concepts.",
        ModuleResponsibility.INFRASTRUCTURE: "Integrates external systems and infrastructure adapters.",
        ModuleResponsibility.DATA_ACCESS: "Handles persistence, repositories, and data access.",
        ModuleResponsibility.CONFIGURATION: "Provides application configuration and settings.",
        ModuleResponsibility.TESTING: "Contains test and testing-support code.",
        ModuleResponsibility.UTILITIES: "Provides reusable helper and utility functionality.",
        ModuleResponsibility.AGENT: "Contains agent-oriented application components.",
        ModuleResponsibility.SERVICE: "Provides service-level application functionality.",
    }

    def analyze(
        self,
        source_files=(),
        code_entities=(),
        dependencies=(),
        call_graphs=(),
    ):
        files = self._materialize_strings(source_files, "source_files")
        entities = self._materialize_objects(code_entities, "code_entities")
        dependencies = self._materialize_objects(dependencies, "dependencies")
        call_graphs = self._materialize_objects(call_graphs, "call_graphs")

        entity_data = self._read_entities(entities)
        dependency_data = self._read_dependencies(dependencies)
        call_data = self._read_call_graphs(call_graphs)

        module_files = {
            self._normalize_path(item) for item in files
        }
        module_files.update(item["filename"] for item in entity_data)
        module_files.update(
            item["source_file"] for item in dependency_data
        )
        module_files.update(item["filename"] for item in call_data)

        module_files = tuple(sorted(module_files))

        findings = []
        unclassified = []

        for file_path in module_files:
            module_entities = [
                item for item in entity_data
                if item["filename"] == file_path
            ]
            module_dependencies = [
                item for item in dependency_data
                if item["source_file"] == file_path
            ]
            module_calls = [
                item for item in call_data
                if item["filename"] == file_path
            ]

            responsibility, evidence, confidence = self._classify(
                file_path,
                module_entities,
                module_dependencies,
                module_calls,
            )

            if responsibility is ModuleResponsibility.UNKNOWN:
                unclassified.append(file_path)
                continue

            findings.append(
                ModuleResponsibilityFinding(
                    module_name=self._module_name(file_path),
                    file_path=file_path,
                    responsibility=responsibility,
                    confidence=confidence,
                    evidence_count=len(evidence),
                    evidence=tuple(evidence),
                    entity_count=len(module_entities),
                    dependency_count=len(module_dependencies),
                    call_count=sum(
                        item["total_calls"] for item in module_calls
                    ),
                    description=self.DESCRIPTIONS[responsibility],
                )
            )

        findings = tuple(
            sorted(findings, key=lambda item: item.file_path)
        )
        unclassified = tuple(sorted(unclassified))

        return ModuleResponsibilityAnalysisResult(
            total_modules=len(module_files),
            classified_modules=len(findings),
            unclassified_modules=len(unclassified),
            findings=findings,
            unclassified_files=unclassified,
            total_entities=len(entity_data),
            total_dependencies=len(dependency_data),
            total_calls=sum(
                item["total_calls"] for item in call_data
            ),
        )

    def _classify(
        self,
        file_path,
        entities,
        dependencies,
        call_graphs,
    ):
        parts = self._path_parts(file_path)
        filename = parts[-1] if parts else ""
        stem = filename.rsplit(".", 1)[0]
        tokens = self._tokenize(stem)

        # Explicit directory placement takes precedence.
        for responsibility, aliases in self.DIRECTORY_RULES.items():
            if set(parts[:-1]) & aliases:
                evidence = [
                    ModuleResponsibilityEvidence(
                        "directory_structure",
                        (
                            f"Module is located in a "
                            f"{responsibility.value} directory."
                        ),
                        file_path,
                    )
                ]
                return (
                    responsibility,
                    evidence,
                    ResponsibilityConfidence.HIGH,
                )

        # Filename indicators.
        for responsibility, indicators in self.NAME_RULES.items():
            if tokens & set(indicators):
                evidence = [
                    ModuleResponsibilityEvidence(
                        "module_name",
                        (
                            f"Module filename indicates "
                            f"{responsibility.value} responsibility."
                        ),
                        file_path,
                    )
                ]
                return (
                    responsibility,
                    evidence,
                    ResponsibilityConfidence.MEDIUM,
                )

        # Entity names provide classification evidence.
        entity_matches = []

        for item in entities:
            entity_tokens = self._tokenize(item["name"])

            for responsibility, indicators in self.NAME_RULES.items():
                if entity_tokens & set(indicators):
                    entity_matches.append((responsibility, item))
                    break

        if entity_matches:
            counts = {}

            for responsibility, _ in entity_matches:
                counts[responsibility] = (
                    counts.get(responsibility, 0) + 1
                )

            selected = sorted(
                counts,
                key=lambda item: (-counts[item], item.value),
            )[0]

            selected_entities = [
                item
                for responsibility, item in entity_matches
                if responsibility is selected
            ]

            evidence = [
                ModuleResponsibilityEvidence(
                    "code_entity",
                    (
                        f"Entity name indicates "
                        f"{selected.value} responsibility."
                    ),
                    file_path,
                    item["name"],
                )
                for item in selected_entities
            ]

            confidence = (
                ResponsibilityConfidence.HIGH
                if len(selected_entities) >= 2
                else ResponsibilityConfidence.MEDIUM
            )

            return selected, evidence, confidence

        return (
            ModuleResponsibility.UNKNOWN,
            [],
            ResponsibilityConfidence.LOW,
        )

    @staticmethod
    def _tokenize(value):
        """Split snake_case, kebab-case, PascalCase and camelCase names."""
        if not isinstance(value, str):
            return set()

        value = value.replace("-", "_")

        # Separate acronym-to-word boundaries, e.g. HTTPServer.
        value = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", value)

        # Separate lowercase/digit-to-uppercase boundaries,
        # e.g. CustomerRepository and userService.
        value = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", value)

        return {
            token.lower()
            for token in value.split("_")
            if token
        }

    @staticmethod
    def _read_entities(entities):
        result = []

        for item in entities:
            required = (
                "name",
                "entity_type",
                "qualified_name",
                "filename",
            )

            if any(not hasattr(item, field) for field in required):
                raise ModuleResponsibilityAnalysisError(
                    "Each code entity must expose name, entity_type, "
                    "qualified_name, and filename."
                )

            values = {
                field: getattr(item, field)
                for field in required
            }

            if any(
                not isinstance(value, str) or not value.strip()
                for value in values.values()
            ):
                raise ModuleResponsibilityAnalysisError(
                    "Code entity fields must be non-empty strings."
                )

            result.append({
                "name": values["name"],
                "entity_type": values["entity_type"],
                "qualified_name": values["qualified_name"],
                "filename": ModuleResponsibilityAnalysisService._normalize_path(
                    values["filename"]
                ),
            })

        return tuple(result)

    @staticmethod
    def _read_dependencies(dependencies):
        result = []

        for item in dependencies:
            if not hasattr(item, "source_file"):
                raise ModuleResponsibilityAnalysisError(
                    "Each dependency must expose source_file."
                )

            source_file = item.source_file

            if not isinstance(source_file, str) or not source_file.strip():
                raise ModuleResponsibilityAnalysisError(
                    "Dependency source_file must be a non-empty string."
                )

            result.append({
                "source_file": ModuleResponsibilityAnalysisService._normalize_path(
                    source_file
                )
            })

        return tuple(result)

    @staticmethod
    def _read_call_graphs(call_graphs):
        result = []

        for item in call_graphs:
            if (
                not hasattr(item, "filename")
                or not hasattr(item, "total_calls")
            ):
                raise ModuleResponsibilityAnalysisError(
                    "Each call graph must expose filename and total_calls."
                )

            filename = item.filename
            total_calls = item.total_calls

            if not isinstance(filename, str) or not filename.strip():
                raise ModuleResponsibilityAnalysisError(
                    "Call graph filename must be a non-empty string."
                )

            if (
                isinstance(total_calls, bool)
                or not isinstance(total_calls, int)
                or total_calls < 0
            ):
                raise ModuleResponsibilityAnalysisError(
                    "Call graph total_calls must be a non-negative integer."
                )

            result.append({
                "filename": ModuleResponsibilityAnalysisService._normalize_path(
                    filename
                ),
                "total_calls": total_calls,
            })

        return tuple(result)

    @staticmethod
    def _materialize_strings(values, label):
        if values is None or isinstance(
            values, (str, bytes, dict, set, frozenset)
        ):
            raise ModuleResponsibilityAnalysisError(
                f"{label} must be an ordered iterable."
            )

        try:
            result = tuple(values)
        except TypeError as exc:
            raise ModuleResponsibilityAnalysisError(
                f"{label} must be iterable."
            ) from exc

        if any(
            not isinstance(item, str) or not item.strip()
            for item in result
        ):
            raise ModuleResponsibilityAnalysisError(
                f"{label} must contain non-empty strings."
            )

        if len(result) != len(set(result)):
            raise ModuleResponsibilityAnalysisError(
                f"{label} must not contain duplicate entries."
            )

        return result

    @staticmethod
    def _materialize_objects(values, label):
        if values is None or isinstance(
            values, (str, bytes, dict, set, frozenset)
        ):
            raise ModuleResponsibilityAnalysisError(
                f"{label} must be an ordered iterable."
            )

        try:
            return tuple(values)
        except TypeError as exc:
            raise ModuleResponsibilityAnalysisError(
                f"{label} must be iterable."
            ) from exc

    @staticmethod
    def _normalize_path(value):
        value = value.replace("\\", "/").strip()

        while value.startswith("./"):
            value = value[2:]

        return value.rstrip("/")

    @staticmethod
    def _path_parts(path):
        return tuple(
            part.lower()
            for part in path.split("/")
            if part
        )

    @staticmethod
    def _module_name(file_path):
        filename = file_path.rsplit("/", 1)[-1]
        return filename.rsplit(".", 1)[0]
