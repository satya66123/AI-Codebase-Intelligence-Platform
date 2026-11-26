# Project Structure

![Python](https://img.shields.io/badge/Python-3.11-blue)
![Streamlit](https://img.shields.io/badge/Framework-Streamlit-red)
![Structure](https://img.shields.io/badge/Documentation-Project_Structure-informational)
[![GitHub](https://img.shields.io/badge/GitHub-Repository-black?logo=github)](https://github.com/satya66123/AI-Codebase-Intelligence-Platform)

## 1. Overview

The **AI Codebase Intelligence Platform** is organized into application, presentation, and test components.

The project uses Python and Streamlit, with services responsible for repository operations, code quality analysis, and AI provider/model management.

## 2. Main Project Areas

The following areas are part of the documented project structure:

```text
AI-Codebase-Intelligence-Platform/
│
├── appy/
│   ├── application/
│   │
│   └── presentation/
│       ├── pages/
│       │   └── home.py
│       │
│       ├── repository_discovery_view.py
│       └── code_quality_view.py
│
├── tests/
│   ├── test_app.py
│   ├── test_json_storage.py
│   └── test_ingestion_journal.py
│
├── docs/
│
├── pytest.ini
└── requirements.txt
```

This is a documentation-level overview of known project paths, not a complete listing of every file in the repository.

## 3. Application Package

### `appy/application/`

Contains application-level coordination and service creation.

The application container is available through:

`appy.application.ApplicationContainer`

Known service creation methods include:

- `create_provider_model_service()`
- `create_repository_discovery_integration_service()`
- `create_repository_source_loading_service()`
- `create_code_quality_analysis_service()`

### `appy/presentation/`

Contains the Streamlit presentation components.

Known modules include:

| File | Responsibility |
|---|---|
| `pages/home.py` | Main application page |
| `repository_discovery_view.py` | Repository discovery interface |
| `code_quality_view.py` | Code quality interface |

## 4. Tests Directory

The `tests/` directory contains automated tests for application functionality.

Known test files include:

- `test_app.py`
- `test_json_storage.py`
- `test_ingestion_journal.py`

The project uses PyTest for automated testing.

## 5. Documentation Directory

The `docs/` directory contains the project's technical and user documentation.

Documents prepared in this documentation series include:

- `API_DOCUMENTATION.md`
- `ARCHITECTURE.md`
- `USER_GUIDE.md`
- `INSTALLATION_GUIDE.md`
- `CONFIGURATION_GUIDE.md`
- `FEATURES_DOCUMENTATION.md`
- `PROJECT_STRUCTURE.md`

## 6. Root-Level Configuration

| File | Purpose |
|---|---|
| `pytest.ini` | PyTest configuration |
| `requirements.txt` | Python dependency list |

## 7. Project Organization Goals

The project structure supports:

- Separation of application and presentation responsibilities
- Centralized application service creation
- Organized automated tests
- Dedicated technical documentation
- Maintainable development and extension

---

![Project Status](https://img.shields.io/badge/Project_Status-Completed-brightgreen)
