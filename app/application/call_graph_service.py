
import ast
from dataclasses import dataclass
from pathlib import Path

from app.application.language_parser import ParsedSource


class CallGraphError(ValueError):
    """Raised when call graph analysis fails."""


@dataclass(frozen=True)
class CallRecord:
    """Represents a function or method call in source code."""

    filename: str
    caller: str
    caller_type: str
    callee: str
    call_type: str
    line: int


@dataclass(frozen=True)
class CallGraphResult:
    """Contains all discovered call relationships for a source file."""

    filename: str
    calls: tuple
    total_calls: int


class _CallVisitor(ast.NodeVisitor):
    """Track caller context while visiting function calls."""

    def __init__(self, filename: str):
        self.filename = filename
        self.module_name = (
            "<module>"
            if filename == "<unknown>"
            else Path(filename).stem
        )
        self.scope_stack = [
            (self.module_name, "module")
        ]
        self.calls = []

    def visit_ClassDef(self, node):
        """Visit a class body using the class as the current scope."""

        self._visit_outer_expressions(
            node.decorator_list + node.bases
        )

        qualified_name = self._qualified_name(node.name)

        self.scope_stack.append((qualified_name, "class"))
        for child in node.body:
            self.visit(child)
        self.scope_stack.pop()

    def visit_FunctionDef(self, node):
        """Visit a function body using the function as the current scope."""

        self._visit_outer_expressions(
            node.decorator_list
            + node.args.defaults
            + node.args.kw_defaults
        )

        self._visit_outer_expressions(
            [
                argument.annotation
                for argument in (
                    node.args.posonlyargs
                    + node.args.args
                    + node.args.kwonlyargs
                )
                if argument.annotation is not None
            ]
        )

        parent_name, parent_type = self.scope_stack[-1]

        caller_type = (
            "method" if parent_type == "class" else "function"
        )
        qualified_name = self._qualified_name(node.name)

        self.scope_stack.append((qualified_name, caller_type))
        for child in node.body:
            self.visit(child)
        self.scope_stack.pop()

    def visit_AsyncFunctionDef(self, node):
        """Visit asynchronous functions using the same scope rules."""

        self.visit_FunctionDef(node)

    def visit_Call(self, node):
        """Record a call and inspect nested calls in its arguments."""

        caller, caller_type = self.scope_stack[-1]
        callee, call_type = self._resolve_callee(node.func)

        self.calls.append(
            CallRecord(
                filename=self.filename,
                caller=caller,
                caller_type=caller_type,
                callee=callee,
                call_type=call_type,
                line=node.lineno,
            )
        )

        self.generic_visit(node)

    def _qualified_name(self, name):
        parent_name, _ = self.scope_stack[-1]
        return f"{parent_name}.{name}"

    def _visit_outer_expressions(self, expressions):
        for expression in expressions:
            if expression is not None:
                self.visit(expression)

    @classmethod
    def _resolve_callee(cls, node):
        """Resolve simple names and attribute chains."""

        if isinstance(node, ast.Name):
            return node.id, "function"

        if isinstance(node, ast.Attribute):
            base, _ = cls._resolve_callee(node.value)
            return f"{base}.{node.attr}", "attribute"

        return "<dynamic>", "dynamic"


class CallGraphService:
    """Extract function-call relationships from a parsed Python file."""

    def analyze(self, parsed_source: ParsedSource) -> CallGraphResult:
        """Build a call graph result from a parsed source file."""

        if not isinstance(parsed_source, ParsedSource):
            raise CallGraphError(
                "Input must be a ParsedSource instance."
            )

        if not isinstance(parsed_source.tree, ast.Module):
            raise CallGraphError(
                "Python source must contain an AST module."
            )

        visitor = _CallVisitor(parsed_source.filename)
        visitor.visit(parsed_source.tree)

        calls = tuple(
            sorted(
                visitor.calls,
                key=lambda record: record.line,
            )
        )

        return CallGraphResult(
            filename=parsed_source.filename,
            calls=calls,
            total_calls=len(calls),
        )
