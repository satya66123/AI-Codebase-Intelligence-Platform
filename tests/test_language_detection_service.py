
from app.application.language_detection_service import (
    LanguageDetectionService,
)


def test_detect_python_language():
    service = LanguageDetectionService()

    assert service.detect_language("main.py") == "Python"


def test_detect_javascript_language():
    service = LanguageDetectionService()

    assert service.detect_language("app.js") == "JavaScript"


def test_detect_typescript_language():
    service = LanguageDetectionService()

    assert service.detect_language("app.ts") == "TypeScript"


def test_detect_language_case_insensitive():
    service = LanguageDetectionService()

    assert service.detect_language("MAIN.PY") == "Python"


def test_detect_special_filename():
    service = LanguageDetectionService()

    assert service.detect_language("Dockerfile") == "Dockerfile"
    assert service.detect_language("Makefile") == "Makefile"


def test_unknown_file_extension():
    service = LanguageDetectionService()

    assert service.detect_language("data.unknown") == "Unknown"


def test_detect_multiple_languages():
    service = LanguageDetectionService()

    files = [
        "main.py",
        "service.py",
        "app.js",
        "index.ts",
        "README.md",
        "data.unknown",
    ]

    result = service.detect_languages(files)

    assert result == {
        "JavaScript": 1,
        "Markdown": 1,
        "Python": 2,
        "TypeScript": 1,
        "Unknown": 1,
    }


def test_supported_extensions():
    service = LanguageDetectionService()

    extensions = service.get_supported_extensions()

    assert ".py" in extensions
    assert ".js" in extensions
    assert ".java" in extensions
    assert ".go" in extensions
