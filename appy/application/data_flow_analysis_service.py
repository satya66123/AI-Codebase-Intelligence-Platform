
import ast
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Iterable

from appy.application.language_parser import ParsedSource


class DataFlowAnalysisError(ValueError):
    """Raised when data flow analysis receives invalid input."""


@dataclass(frozen=True)
class DataFlowNode:
    """Represents a data source, transformation, or destination."""

    node_id: str
    file_path: str
    scope: str
    name: str
    operation: str
    line: int
    expression: str
    origin_type: str

    def __post_init__(self):
        for field_name in (
            "node_id",
            "file_path",
            "scope",
            "name",
            "operation",
            "expression",
            "origin_type",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise DataFlowAnalysisError(
                    f"{field_name} must be a non-empty string."
                )

        if (
            isinstance(self.line, bool)
            or not isinstance(self.line, int)
            or self.line < 1
        ):
            raise DataFlowAnalysisError(
                "Node line must be a positive integer."
            )


@dataclass(frozen=True)
class DataFlowEdge:
    """Represents data moving from one node to another."""

    source_node: str
    target_node: str
    relationship_type: str
    line: int

    def __post_init__(self):
        for field_name in (
            "source_node",
            "target_node",
            "relationship_type",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise DataFlowAnalysisError(
                    f"{field_name} must be a non-empty string."
                )

        if (
            isinstance(self.line, bool)
            or not isinstance(self.line, int)
            or self.line < 1
        ):
            raise DataFlowAnalysisError(
                "Edge line must be a positive integer."
            )


@dataclass(frozen=True)
class DataFlowPath:
    """Represents a source-to-destination data flow path."""

    nodes: tuple
    relationship_types: tuple

    def __post_init__(self):
        if not isinstance(self.nodes, tuple) or len(self.nodes) < 2:
            raise DataFlowAnalysisError(
                "A data flow path must contain at least two nodes."
            )

        if not isinstance(self.relationship_types, tuple):
            raise DataFlowAnalysisError(
                "Path relationship types must be a tuple."
            )

        if len(self.relationship_types) != len(self.nodes) - 1:
            raise DataFlowAnalysisError(
                "Path relationship count must match its nodes."
            )


@dataclass(frozen=True)
class DataFlowAnalysisResult:
    """Contains data flow nodes, edges, and discovered paths."""

    file_path: str
    language: str
    total_nodes: int
    total_edges: int
    total_paths: int
    nodes: tuple
    edges: tuple
    paths: tuple
    analyzed: bool
    syntax_error: str = ""

    def __post_init__(self):
        for field_name in (
            "file_path",
            "language",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise DataFlowAnalysisError(
                    f"{field_name} must be a non-empty string."
                )

        for field_name in (
            "total_nodes",
            "total_edges",
            "total_paths",
        ):
            value = getattr(self, field_name)
            if (
                isinstance(value, bool)
                or not isinstance(value, int)
                or value < 0
            ):
                raise DataFlowAnalysisError(
                    f"{field_name} must be a non-negative integer."
                )

        for field_name in ("nodes", "edges", "paths"):
            if not isinstance(getattr(self, field_name), tuple):
                raise DataFlowAnalysisError(
                    f"{field_name} must be a tuple."
                )

        if self.total_nodes != len(self.nodes):
            raise DataFlowAnalysisError(
                "Total nodes must match the nodes collection."
            )

        if self.total_edges != len(self.edges):
            raise DataFlowAnalysisError(
                "Total edges must match the edges collection."
            )

        if self.total_paths != len(self.paths):
            raise DataFlowAnalysisError(
                "Total paths must match the paths collection."
            )

        if not isinstance(self.analyzed, bool):
            raise DataFlowAnalysisError(
                "Analyzed must be a boolean."
            )

        if not isinstance(self.syntax_error, str):
            raise DataFlowAnalysisError(
                "Syntax error must be a string."
            )

    @property
    def has_data_flow(self):
        return bool(self.edges)

    @property
    def healthy(self):
        return self.analyzed and not self.syntax_error

    @property
    def source_nodes(self):
        targets = {edge.target_node for edge in self.edges}
        return tuple(
            node for node in self.nodes
            if node.node_id not in targets
        )

    @property
    def destination_nodes(self):
        sources = {edge.source_node for edge in self.edges}
        return tuple(
            node for node in self.nodes
            if node.node_id not in sources
        )

    @property
    def assignment_nodes(self):
        return tuple(
            node for node in self.nodes
            if node.operation in {"assignment", "annotated_assignment"}
        )

    @property
    def parameter_nodes(self):
        return tuple(
            node for node in self.nodes
            if node.operation == "parameter"
        )

    @property
    def return_nodes(self):
        return tuple(
            node for node in self.nodes
            if node.operation == "return"
        )

    @property
    def call_nodes(self):
        return tuple(
            node for node in self.nodes
            if node.operation == "call"
        )


class _DataFlowVisitor(ast.NodeVisitor):
    """Collect conservative intraprocedural data flow from Python AST."""

    def __init__(self, filename):
        self.filename = filename
        self.nodes = []
        self.edges = []
        self.scope_stack = ["<module>"]
        self.variable_stack = [{}]
        self.node_counter = 0

    @property
    def scope(self):
        return ".".join(self.scope_stack)

    def _new_node(
        self,
        name,
        operation,
        line,
        expression,
        origin_type,
    ):
        self.node_counter += 1
        node = DataFlowNode(
            node_id=f"{self.filename}::data::{self.node_counter}",
            file_path=self.filename,
            scope=self.scope,
            name=name,
            operation=operation,
            line=max(1, line or 1),
            expression=expression,
            origin_type=origin_type,
        )
        self.nodes.append(node)
        return node

    def _add_edge(self, source, target, relationship, line):
        if source.node_id == target.node_id:
            return

        edge = DataFlowEdge(
            source_node=source.node_id,
            target_node=target.node_id,
            relationship_type=relationship,
            line=max(1, line or 1),
        )
        self.edges.append(edge)

    @staticmethod
    def _expression(node):
        try:
            return ast.unparse(node)
        except (AttributeError, TypeError):
            return "<expression>"

    @staticmethod
    def _names_in_expression(node):
        names = []
        seen = set()

        for child in ast.walk(node):
            if isinstance(child, ast.Name) and isinstance(
                child.ctx, ast.Load
            ):
                if child.id not in seen:
                    names.append(child.id)
                    seen.add(child.id)

        return tuple(names)

    def _resolve_variable(self, name):
        for variables in reversed(self.variable_stack):
            if name in variables:
                return variables[name]
        return None

    def _record_assignment(self, target, value, line, operation):
        if isinstance(target, (ast.Tuple, ast.List)):
            for item in target.elts:
                self._record_assignment(
                    item,
                    value,
                    line,
                    operation,
                )
            return

        if not isinstance(target, ast.Name):
            return

        expression = self._expression(value)
        previous = self._resolve_variable(target.id)
        node = self._new_node(
            name=target.id,
            operation=operation,
            line=line,
            expression=expression,
            origin_type="derived",
        )

        # Preserve the previous value as an explicit data-flow predecessor.
        # This is distinct from ordinary assignment edges created for names
        # referenced by the right-hand-side expression.
        if previous is not None:
            self._add_edge(previous, node, "reassignment", line)

        names = self._names_in_expression(value)
        linked_sources = []

        for name in names:
            source = self._resolve_variable(name)
            if source is not None:
                self._add_edge(
                    source,
                    node,
                    "assignment",
                    line,
                )
                linked_sources.append(source)

        if not linked_sources:
            node = self._replace_origin_type(
                node,
                "expression",
            )

        self.variable_stack[-1][target.id] = node

    def _replace_origin_type(self, node, origin_type):
        replacement = DataFlowNode(
            node_id=node.node_id,
            file_path=node.file_path,
            scope=node.scope,
            name=node.name,
            operation=node.operation,
            line=node.line,
            expression=node.expression,
            origin_type=origin_type,
        )
        self.nodes[-1] = replacement
        return replacement

    def visit_FunctionDef(self, node):
        self._visit_function(node)

    def visit_AsyncFunctionDef(self, node):
        self._visit_function(node)

    def _visit_function(self, node):
        # Defaults and decorators are evaluated in the enclosing scope.
        for decorator in node.decorator_list:
            self.visit(decorator)

        for default in node.args.defaults:
            self.visit(default)

        for default in node.args.kw_defaults:
            if default is not None:
                self.visit(default)

        self.scope_stack.append(node.name)
        self.variable_stack.append({})

        arguments = (
            node.args.posonlyargs
            + node.args.args
            + node.args.kwonlyargs
        )

        if node.args.vararg is not None:
            arguments.append(node.args.vararg)

        if node.args.kwarg is not None:
            arguments.append(node.args.kwarg)

        for argument in arguments:
            parameter = self._new_node(
                name=argument.arg,
                operation="parameter",
                line=argument.lineno,
                expression=argument.arg,
                origin_type="input",
            )
            self.variable_stack[-1][argument.arg] = parameter

        for statement in node.body:
            self.visit(statement)

        self.variable_stack.pop()
        self.scope_stack.pop()

    def visit_ClassDef(self, node):
        for decorator in node.decorator_list:
            self.visit(decorator)

        for base in node.bases:
            self.visit(base)

        self.scope_stack.append(node.name)
        self.variable_stack.append({})

        for statement in node.body:
            self.visit(statement)

        self.variable_stack.pop()
        self.scope_stack.pop()

    def visit_Assign(self, node):
        self.visit(node.value)

        for target in node.targets:
            self._record_assignment(
                target,
                node.value,
                node.lineno,
                "assignment",
            )

    def visit_AnnAssign(self, node):
        if node.value is not None:
            self.visit(node.value)
            self._record_assignment(
                node.target,
                node.value,
                node.lineno,
                "annotated_assignment",
            )

    def visit_AugAssign(self, node):
        self.visit(node.value)

        if isinstance(node.target, ast.Name):
            previous = self._resolve_variable(node.target.id)
            expression = self._expression(node.value)

            node_result = self._new_node(
                name=node.target.id,
                operation="assignment",
                line=node.lineno,
                expression=expression,
                origin_type="derived",
            )

            if previous is not None:
                self._add_edge(
                    previous,
                    node_result,
                    "reassignment",
                    node.lineno,
                )

            for name in self._names_in_expression(node.value):
                source = self._resolve_variable(name)
                if source is not None:
                    self._add_edge(
                        source,
                        node_result,
                        "assignment",
                        node.lineno,
                    )

            self.variable_stack[-1][node.target.id] = node_result

    def visit_Call(self, node):
        self.visit(node.func)

        for argument in node.args:
            self.visit(argument)

        for keyword in node.keywords:
            self.visit(keyword.value)

        call_name = self._expression(node.func)
        call_node = self._new_node(
            name=call_name,
            operation="call",
            line=node.lineno,
            expression=self._expression(node),
            origin_type="computed",
        )

        for argument in list(node.args) + [
            keyword.value for keyword in node.keywords
        ]:
            for name in self._names_in_expression(argument):
                source = self._resolve_variable(name)
                if source is not None:
                    self._add_edge(
                        source,
                        call_node,
                        "argument",
                        node.lineno,
                    )

    def visit_Return(self, node):
        if node.value is None:
            return

        self.visit(node.value)

        return_node = self._new_node(
            name="return",
            operation="return",
            line=node.lineno,
            expression=self._expression(node.value),
            origin_type="output",
        )

        for name in self._names_in_expression(node.value):
            source = self._resolve_variable(name)
            if source is not None:
                self._add_edge(
                    source,
                    return_node,
                    "return",
                    node.lineno,
                )

    def visit_For(self, node):
        self.visit(node.iter)

        if isinstance(node.target, ast.Name):
            iterator_node = self._new_node(
                name=node.target.id,
                operation="assignment",
                line=node.lineno,
                expression=self._expression(node.iter),
                origin_type="derived",
            )
            for name in self._names_in_expression(node.iter):
                source = self._resolve_variable(name)
                if source is not None:
                    self._add_edge(
                        source,
                        iterator_node,
                        "iteration",
                        node.lineno,
                    )
            self.variable_stack[-1][node.target.id] = iterator_node

        for statement in node.body:
            self.visit(statement)

        for statement in node.orelse:
            self.visit(statement)

    def visit_AsyncFor(self, node):
        self.visit_For(node)

    def visit_With(self, node):
        for item in node.items:
            self.visit(item.context_expr)

            if isinstance(item.optional_vars, ast.Name):
                context_node = self._new_node(
                    name=item.optional_vars.id,
                    operation="assignment",
                    line=node.lineno,
                    expression=self._expression(item.context_expr),
                    origin_type="derived",
                )
                for name in self._names_in_expression(
                    item.context_expr
                ):
                    source = self._resolve_variable(name)
                    if source is not None:
                        self._add_edge(
                            source,
                            context_node,
                            "context",
                            node.lineno,
                        )
                self.variable_stack[-1][
                    item.optional_vars.id
                ] = context_node

        for statement in node.body:
            self.visit(statement)

    def visit_AsyncWith(self, node):
        self.visit_With(node)


class DataFlowAnalysisService:
    """Analyze statically identifiable data flows in parsed Python sources."""

    SUPPORTED_LANGUAGES = {"python", "py"}

    def analyze(
        self,
        parsed_sources: Iterable[ParsedSource],
    ) -> tuple:
        """Analyze one or more parsed source files."""
        sources = self._materialize_sources(parsed_sources)
        results = []

        for parsed_source in sources:
            language = parsed_source.language.lower()

            if language not in self.SUPPORTED_LANGUAGES:
                results.append(
                    self._empty_result(
                        parsed_source.filename,
                        parsed_source.language,
                        analyzed=False,
                        syntax_error="Unsupported language.",
                    )
                )
                continue

            if not isinstance(parsed_source.tree, ast.Module):
                results.append(
                    self._empty_result(
                        parsed_source.filename,
                        parsed_source.language,
                        analyzed=False,
                        syntax_error="Python source must contain an AST module.",
                    )
                )
                continue

            visitor = _DataFlowVisitor(parsed_source.filename)

            try:
                visitor.visit(parsed_source.tree)
            except Exception as exc:
                raise DataFlowAnalysisError(
                    f"Data flow analysis failed for "
                    f"{parsed_source.filename}: {exc}"
                ) from exc

            nodes = tuple(
                sorted(
                    visitor.nodes,
                    key=lambda item: (
                        item.line,
                        item.scope,
                        item.name,
                        item.node_id,
                    ),
                )
            )

            edges = tuple(
                sorted(
                    set(visitor.edges),
                    key=lambda item: (
                        item.line,
                        item.source_node,
                        item.target_node,
                        item.relationship_type,
                    ),
                )
            )

            paths = tuple(
                DataFlowPath(
                    nodes=(edge.source_node, edge.target_node),
                    relationship_types=(edge.relationship_type,),
                )
                for edge in edges
            )

            results.append(
                DataFlowAnalysisResult(
                    file_path=parsed_source.filename,
                    language=parsed_source.language,
                    total_nodes=len(nodes),
                    total_edges=len(edges),
                    total_paths=len(paths),
                    nodes=nodes,
                    edges=edges,
                    paths=paths,
                    analyzed=True,
                    syntax_error="",
                )
            )

        return tuple(results)

    @staticmethod
    def _materialize_sources(parsed_sources):
        if parsed_sources is None or isinstance(
            parsed_sources,
            (str, bytes, dict, set, frozenset),
        ):
            raise DataFlowAnalysisError(
                "parsed_sources must be an ordered iterable of ParsedSource objects."
            )

        try:
            sources = tuple(parsed_sources)
        except TypeError as exc:
            raise DataFlowAnalysisError(
                "parsed_sources must be iterable."
            ) from exc

        if not all(
            isinstance(source, ParsedSource)
            for source in sources
        ):
            raise DataFlowAnalysisError(
                "Every source must be a ParsedSource instance."
            )

        filenames = [source.filename for source in sources]
        if len(filenames) != len(set(filenames)):
            raise DataFlowAnalysisError(
                "Parsed source filenames must be unique."
            )

        return sources

    @staticmethod
    def _empty_result(
        filename,
        language,
        analyzed,
        syntax_error,
    ):
        return DataFlowAnalysisResult(
            file_path=filename,
            language=language,
            total_nodes=0,
            total_edges=0,
            total_paths=0,
            nodes=(),
            edges=(),
            paths=(),
            analyzed=analyzed,
            syntax_error=syntax_error,
        )

