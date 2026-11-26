
from pathlib import Path


class LanguageDetectionService:
    """Detects programming languages from repository files."""

    LANGUAGE_EXTENSIONS = {
        ".py": "Python",
        ".js": "JavaScript",
        ".jsx": "JavaScript",
        ".ts": "TypeScript",
        ".tsx": "TypeScript",
        ".java": "Java",
        ".kt": "Kotlin",
        ".kts": "Kotlin",
        ".c": "C",
        ".h": "C",
        ".cpp": "C++",
        ".cc": "C++",
        ".hpp": "C++",
        ".cs": "C#",
        ".go": "Go",
        ".rs": "Rust",
        ".rb": "Ruby",
        ".php": "PHP",
        ".swift": "Swift",
        ".dart": "Dart",
        ".scala": "Scala",
        ".r": "R",
        ".m": "Objective-C",
        ".sql": "SQL",
        ".sh": "Shell",
        ".bash": "Shell",
        ".ps1": "PowerShell",
        ".html": "HTML",
        ".htm": "HTML",
        ".css": "CSS",
        ".scss": "SCSS",
        ".less": "Less",
        ".xml": "XML",
        ".json": "JSON",
        ".yaml": "YAML",
        ".yml": "YAML",
        ".toml": "TOML",
        ".md": "Markdown",
        ".rst": "reStructuredText",
        ".vue": "Vue",
        ".svelte": "Svelte",
    }

    SPECIAL_FILENAMES = {
        "dockerfile": "Dockerfile",
        "makefile": "Makefile",
        "jenkinsfile": "Groovy",
        "gemfile": "Ruby",
        "rakefile": "Ruby",
    }

    def detect_language(self, file_path: str | Path) -> str:
        """Return the detected language or Unknown."""

        path = Path(file_path)
        filename = path.name.lower()

        if filename in self.SPECIAL_FILENAMES:
            return self.SPECIAL_FILENAMES[filename]

        return self.LANGUAGE_EXTENSIONS.get(
            path.suffix.lower(),
            "Unknown"
        )

    def detect_languages(self, file_paths) -> dict:
        """Count files by detected language."""

        language_counts = {}

        for file_path in file_paths:
            language = self.detect_language(file_path)

            language_counts[language] = (
                language_counts.get(language, 0) + 1
            )

        return dict(sorted(language_counts.items()))

    def get_supported_extensions(self) -> tuple:
        """Return all supported file extensions."""

        return tuple(sorted(self.LANGUAGE_EXTENSIONS.keys()))
