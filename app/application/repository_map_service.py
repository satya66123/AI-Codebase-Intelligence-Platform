
from pathlib import Path

from app.application.repository_scanner import RepositoryScanResult


class RepositoryMapError(ValueError):
    """Raised when repository map generation fails."""


class RepositoryMapService:
    """Generates a readable directory tree for a repository."""

    def build_map(
        self,
        result: RepositoryScanResult,
        include_files: bool = True
    ) -> str:
        if not isinstance(result, RepositoryScanResult):
            raise RepositoryMapError(
                "A valid RepositoryScanResult object is required."
            )

        root = result.root

        tree = {}

        def get_node(relative_path: Path):
            node = tree

            for part in relative_path.parts:
                node = node.setdefault(part, {})

            return node

        try:
            for directory in result.directories:
                relative_path = directory.relative_to(root)
                get_node(relative_path)

            if include_files:
                for file_path in result.files:
                    relative_path = file_path.relative_to(root)
                    get_node(relative_path)

            for symlink in result.symlinks:
                relative_path = symlink.relative_to(root)
                get_node(relative_path)

        except ValueError as exc:
            raise RepositoryMapError(
                "An entry exists outside the repository root."
            ) from exc

        lines = [root.name]

        def render_node(node, prefix=""):
            entries = sorted(
                node.items(),
                key=lambda item: item[0].lower()
            )

            for index, (name, children) in enumerate(entries):
                is_last = index == len(entries) - 1

                connector = "└── " if is_last else "├── "
                lines.append(prefix + connector + name)

                if children:
                    extension = "    " if is_last else "│   "
                    render_node(children, prefix + extension)

        render_node(tree)

        return "\n".join(lines)
