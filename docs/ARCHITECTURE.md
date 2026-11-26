# Architecture

![Python](https://img.shields.io/badge/Python-3.11-blue)
![Streamlit](https://img.shields.io/badge/UI-Streamlit-red)
![Architecture](https://img.shields.io/badge/Architecture-Layered-informational)
[![GitHub](https://img.shields.io/badge/GitHub-Repository-black?logo=github)](https://github.com/satya66123/AI-Codebase-Intelligence-Platform)

## 1. Overview

The **AI Codebase Intelligence Platform** is designed to help developers understand and analyze software repositories using AI-assisted code intelligence.

The application combines repository discovery, source-code analysis, code navigation, retrieval, and multi-provider AI model integration through a Streamlit interface.

Its architecture separates presentation, application coordination, and service responsibilities to keep the platform organized and maintainable.

## 2. High-Level Architecture

The platform follows a layered application structure:

```text
                  User
                   |
                   v
           Streamlit Interface
                   |
                   v
          Presentation Layer
                   |
                   v
          Application Layer
                   |
                   v
             Service Layer
             /     |      \
            v      v       v
       Repository  Code   Provider &
       Services   Analysis Model Services
            \      |       /
             \     |      /
                   v
          Data and Source Handling
                   |
                   v
          Repository Source Files
```

This diagram represents the logical responsibilities of the application, rather than a complete module-by-module dependency map.

## 3. Main Architectural Layers

### Presentation Layer

Responsible for displaying the application interface and handling user interactions.

Known interface components include:

- `appy/presentation/pages/home.py`
- `appy/presentation/repository_discovery_view.py`
- `appy/presentation/code_quality_view.py`

The presentation layer delegates application work to the relevant services instead of owning the underlying analysis logic.

### Application Layer

Coordinates application operations and provides the services required by presentation components.

The application container is available through:

`appy.application.ApplicationContainer`

Known service creation methods include:

- `create_provider_model_service()`
- `create_repository_discovery_integration_service()`
- `create_repository_source_loading_service()`
- `create_code_quality_analysis_service()`

### Service Layer

Contains the operations used by the application to perform repository and code intelligence tasks.

Known service responsibilities include:

- Repository discovery integration
- Repository source loading
- Code quality analysis
- AI provider and model management

### Data and Source Handling

The platform works with repository source files as inputs to its analysis workflows.

Source loading and handling are coordinated through the repository source loading service. Exact storage mechanisms and persistence responsibilities should be documented separately after checking the current implementation.

## 4. Multi-Provider and Multi-Model Architecture

The platform is designed to support multiple AI providers and models.

The configured provider ecosystem includes:

1. Ollama
2. OpenAI
3. Anthropic
4. Google Gemini
5. Mistral
6. Groq
7. Cohere
8. DeepSeek

Provider and model selection is coordinated through the provider model service.

This design allows the application to work with different AI providers instead of depending on a single model vendor.

## 5. Main Application Flow

A simplified application workflow is:

1. The user opens the Streamlit application.
2. The presentation layer displays the available application features.
3. The user selects a repository-related operation.
4. The application layer coordinates the required services.
5. Repository source loading provides source files for the requested operation.
6. The relevant analysis service processes the available inputs.
7. Results are returned to the presentation layer for display.

AI provider and model services are used by the relevant AI-enabled workflows.

## 6. Architecture Goals

The architecture aims to provide:

- Separation of presentation and application responsibilities
- Reusable application services
- Multi-provider and multi-model support
- Maintainable repository-analysis workflows
- Extensible code intelligence capabilities
- A clear foundation for future enhancements

## 7. Design Notes

This document describes the high-level architecture. It does not claim that every possible code-analysis capability is implemented or that the diagram represents every runtime dependency.

Detailed module relationships, data structures, and execution paths should be maintained in their respective technical documents as the implementation is verified.

---

![Project Status](https://img.shields.io/badge/Project_Status-Completed-brightgreen)
