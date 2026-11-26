# API Documentation — AI Codebase Intelligence Platform

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11-blue?logo=python" alt="Python">
  <img src="https://img.shields.io/badge/Framework-Streamlit-red?logo=streamlit" alt="Streamlit">
  <img src="https://img.shields.io/badge/API-Application%20Services-purple" alt="Application Services">
  <a href="https://github.com/satya66123/AI-Codebase-Intelligence-Platform">
    <img src="https://img.shields.io/badge/GitHub-Repository-black?logo=github" alt="GitHub">
  </a>
</p>

## 1. Overview

This document describes the application interfaces and service integration approach used by the AI Codebase Intelligence Platform.

The application uses Python-based application services and Streamlit presentation components to coordinate repository discovery, source loading and code quality analysis.

**Note:** This documentation covers the identifiable application interfaces. It does not claim that a public REST API is implemented.

## 2. Application Entry Point

The application is launched through Streamlit:

```bash
streamlit run app.py
```

The presentation layer provides navigation between the application's main pages.

## 3. Main Application Interfaces

| Interface | Responsibility |
|---|---|
| `render()` | Application navigation and page selection |
| `render_home()` | Home page and provider/model selection |
| `render_repository_discovery()` | Repository discovery workflow |
| `render_code_quality()` | Code quality analysis workflow |

**Module:** `appy/presentation/pages/home.py`

## 4. Application Service Integration

The application container provides service creation methods.

| Method | Purpose |
|---|---|
| `create_provider_model_service()` | Creates provider/model service |
| `create_repository_discovery_integration_service()` | Creates repository discovery integration |
| `create_repository_source_loading_service()` | Creates source loading service |
| `create_code_quality_analysis_service()` | Creates code quality analysis service |

## 5. Repository Discovery Interface

The Repository Discovery page integrates the discovery and source loading services.

```python
render_repository_discovery_view(
    discovery_service,
    source_loading_service,
)
```

The interface coordinates repository discovery and source-file loading.

## 6. Code Quality Analysis Interface

The Code Quality page uses the source files loaded during repository discovery.

```python
render_code_quality_view(
    source_files=source_files,
    service=quality_service,
)
```

The input `source_files` contains the loaded repository source files.

## 7. Provider and Model Interface

The provider/model service exposes the following methods:

```python
providers = service.get_providers()

models = service.get_models(provider)
```

The application uses these methods to populate provider and model selection controls.

## 8. Error Handling and Validation

Application services are responsible for validating their inputs and handling errors according to their implemented contracts.

Repository availability and loaded source data should be checked before starting dependent analysis workflows.

## 9. API Extension

Future API documentation can include additional details when verified from the implementation:

- Public HTTP endpoints, if introduced.
- Request and response schemas.
- Authentication requirements.
- Error response formats.
- Service-specific method signatures.
- Provider integration contracts.

## 10. Related Resources

- [GitHub Repository](https://github.com/satya66123/AI-Codebase-Intelligence-Platform)
- [Streamlit Documentation](https://docs.streamlit.io/)
- [Python Documentation](https://docs.python.org/3/)

---

<p align="center">
  <img src="https://img.shields.io/badge/Project%20Status-Completed-brightgreen?style=for-the-badge" alt=" Completed">
</p>