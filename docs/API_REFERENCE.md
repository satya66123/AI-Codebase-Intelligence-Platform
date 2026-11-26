# API Reference

![Python](https://img.shields.io/badge/Python-3.11-blue)
![API](https://img.shields.io/badge/Documentation-API_Reference-informational)
![Architecture](https://img.shields.io/badge/Architecture-Service_Based-blue)
![License](https://img.shields.io/badge/License-MIT-green)
[![GitHub](https://img.shields.io/badge/GitHub-Repository-black?logo=github)](https://github.com/satya66123/AI-Codebase-Intelligence-Platform)

## 1. Overview

The **AI Codebase Intelligence Platform** provides application interfaces for repository discovery, source loading, code quality analysis, and AI provider/model management.

This reference documents the known application interfaces. It is not a public REST API specification.

## 2. Application Container

**Module:**

`appy.application.ApplicationContainer`

The application container creates the services required by application workflows.

### Known Service Creation Methods

| Method | Responsibility |
|---|---|
| `create_provider_model_service()` | Creates the provider model service |
| `create_repository_discovery_integration_service()` | Creates the repository discovery integration service |
| `create_repository_source_loading_service()` | Creates the repository source loading service |
| `create_code_quality_analysis_service()` | Creates the code quality analysis service |

## 3. Provider Model Service

The provider model service manages provider and model discovery.

### `get_providers()`

Retrieves the configured AI providers.

```python
providers = service.get_providers()
```

### `get_models(provider)`

Retrieves the models associated with a selected provider.

```python
models = service.get_models(provider)
```

The exact return types and parameter constraints should be taken from the current implementation.

## 4. Presentation Interfaces

### Home Page

**Module:**

`appy/presentation/pages/home.py`

Known interface functions:

- `render`
- `render_home`
- `render_repository_discovery`
- `render_code_quality`

These functions belong to the application's presentation workflow.

### Repository Discovery View

**Module:**

`appy/presentation/repository_discovery_view.py`

Known interface:

```python
render_repository_discovery_view(
    discovery_service,
    source_loading_service
)
```

The view receives the repository discovery and source-loading services.

### Code Quality View

**Module:**

`appy/presentation/code_quality_view.py`

Known interface:

```python
render_code_quality_view(
    source_files=source_files,
    service=quality_service
)
```

The view receives source files and the code quality analysis service.

## 5. Main Application Integration Flow

The known application integration flow is:

1. The application container creates the required services.
2. The presentation layer obtains the relevant services.
3. Repository discovery and source loading are coordinated.
4. Source files are supplied to the code quality workflow.
5. The presentation components display the available results.

## 6. Supported AI Provider Ecosystem

The configured provider ecosystem includes:

| Provider | Execution Type |
|---|---|
| Ollama | Local |
| OpenAI | Cloud |
| Anthropic | Cloud |
| Google Gemini | Cloud |
| Mistral | Cloud |
| Groq | Cloud |
| Cohere | Cloud |
| DeepSeek | Cloud |

The configured model collection contains 30 models.

## 7. API Reference Scope

This document covers known Python application interfaces.

It does not claim the existence of:

- Public HTTP REST endpoints
- External API routes
- OpenAPI or Swagger specifications
- Unverified request or response schemas

For exact method signatures, parameter types, return types, and exceptions, consult the corresponding Python source files.

## 8. Conclusion

The platform exposes application-level interfaces through its application container, services, and presentation components.

These interfaces coordinate repository discovery, source loading, code quality analysis, and AI provider/model management.

---

![Project Status](https://img.shields.io/badge/Project_Status-Completed-brightgreen)
