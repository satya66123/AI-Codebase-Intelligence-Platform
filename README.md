# AI Codebase Intelligence Platform

[![Python](https://img.shields.io/badge/Python-3.11-blue.svg)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-App-red.svg)](https://streamlit.io/)
[![PyTest](https://img.shields.io/badge/Tests-3147%20Passed-brightgreen.svg)](https://pytest.org/)
[![CI](https://github.com/satya66123/AI-Codebase-Intelligence-Platform/actions/workflows/python-tests.yml/badge.svg)](https://github.com/satya66123/AI-Codebase-Intelligence-Platform/actions/workflows/python-tests.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Version](https://img.shields.io/badge/Version-1.0.0-blue.svg)](https://github.com/satya66123/AI-Codebase-Intelligence-Platform)

An AI-powered platform designed to help developers discover, understand, analyze, and investigate software repositories using code intelligence and multiple AI providers.

---

## Project Overview

The **AI Codebase Intelligence Platform** simplifies codebase exploration and improves developers' understanding of complex software projects.

It combines repository discovery, structural code analysis, AI-powered reasoning, and advanced code intelligence to help developers investigate repositories and understand how their code is organized and connected.

The platform supports local AI models through Ollama and integrations with cloud AI providers.

## Key Features

### 1. Repository Discovery
- Select and explore local repositories.
- Discover files and directories recursively.
- Apply repository scanning and ignore rules.
- Identify programming languages and file extensions.
- Extract repository metadata and statistics.
- Build repository maps and indexes.

### 2. Code Understanding
- Analyze source code structure.
- Identify functions, methods, classes, and modules.
- Examine imports and dependencies.
- Analyze function calls and inheritance relationships.
- Identify application entry points.
- Inspect configuration and environment references.

### 3. AI Codebase Intelligence
- Ask questions about a repository.
- Understand code functionality and relationships.
- Retrieve relevant source-code context.
- Investigate dependencies and execution paths.
- Generate context-aware explanations.
- Validate answers against available code evidence.

### 4. Advanced Code Intelligence
- Analyze code patterns and structural relationships.
- Investigate potential code quality issues.
- Examine dependency relationships.
- Analyze potential circular dependencies.
- Investigate change impact and technical debt.
- Generate engineering insights and reports.

## Architecture Overview

The platform follows a layered application architecture that separates presentation, application workflows, analysis services, AI integration, and data storage.

```text
                 USER
                  |
                  v
          STREAMLIT INTERFACE
                  |
                  v
          APPLICATION LAYER
                  |
       +----------+----------+
       |          |          |
       v          v          v
   REPOSITORY   CODE       AI
   DISCOVERY   ANALYSIS  INTELLIGENCE
       |          |          |
       +----------+----------+
                  |
                  v
          ADVANCED ANALYSIS
                  |
                  v
          AI PROVIDER LAYER
                  |
       +----------+----------+
       |          |          |
       v          v          v
     OLLAMA     OPENAI    ANTHROPIC
       |          |          |
       +----------+----------+
                  |
                  v
          JSON-BASED STORAGE
```

For more details, see [Architecture Documentation](docs/ARCHITECTURE.md) and [System Design](docs/systemdesign.md).

## Development Phases

| Phase | Name | Status |
|---|---|---|
| Phase 0 | General Foundation | Completed |
| Phase 1 | Repository Discovery Process | Completed |
| Phase 2 | Code Understanding Process | Completed |
| Phase 3 | AI Codebase Intelligence Process | Completed |
| Phase 4 | Advanced Code Intelligence Process | Completed |

### Phase 0 — General Foundation
Established the application foundation, configuration, provider abstraction, logging, error handling, testing setup, and development infrastructure.

### Phase 1 — Repository Discovery Process
Established repository selection, validation, scanning, file discovery, language detection, metadata extraction, and repository mapping.

### Phase 2 — Code Understanding Process
Introduced source-code parsing, code entity extraction, dependency analysis, call relationships, inheritance analysis, and entry-point detection.

### Phase 3 — AI Codebase Intelligence Process
Introduced question analysis, intent detection, repository and code retrieval, context building, AI reasoning, and evidence validation.

### Phase 4 — Advanced Code Intelligence Process
Introduced advanced structural analysis, code quality investigation, dependency analysis, change-impact investigation, risk analysis, and engineering reports.

For the development plan and phase details, see:
- [Project Notes](docs/projectnotes.md)
- [Project Planner](docs/planner.md)
- [Development Steps](docs/steps.md)
- [Project Summary](docs/PROJECT_SUMMARY.md)

## Technology Stack

| Category | Technologies |
|---|---|
| Programming Language | Python 3.11 |
| User Interface | Streamlit |
| AI Integration | Ollama and cloud AI providers |
| Code Analysis | Python parsing and analysis components |
| Storage | JSON-based storage |
| Testing | PyTest |
| Version Control | Git and GitHub |
| CI Configuration | GitHub Actions |
| Container Configuration | Docker |

## Multi-Provider AI Support

The application supports eight AI provider families and 30 configured models.

| Provider | Configured Models |
|---|---:|
| Ollama | 9 |
| OpenAI | 3 |
| Anthropic | 3 |
| Google Gemini | 3 |
| Mistral | 3 |
| Groq | 3 |
| Cohere | 3 |
| DeepSeek | 3 |
| **Total** | **30** |

### Ollama Models
- `qwen2.5:1.5b`
- `gemma2:2b`
- `gemma3:4b`
- `mistral:latest`
- `phi3:latest`
- `qwen3:latest`
- `llama3.1:latest`
- `llama3:8b`
- `deepseek-coder:latest`

### OpenAI Models
- `gpt-5-mini`
- `gpt-4o`
- `gpt-4o-mini`

### Anthropic Models
- `claude-sonnet-4-5`
- `claude-haiku-4-5`
- `claude-opus-4-1`

### Google Gemini Models
- `gemini-3.6-flash`
- `gemini-2.5-flash`
- `gemini-2.5-pro`

The remaining provider model identifiers are maintained in the application's provider configuration.

See [AI Provider Documentation](docs/AI_PROVIDER_DOCUMENTATION.md) and [Configuration Guide](docs/CONFIGURATION_GUIDE.md).

## Project Structure

The application is organized into separate areas for application logic, domain components, infrastructure, presentation, tests, and documentation.

```text
AI-Codebase-Intelligence-Platform/
|
+-- app/
|   +-- application/
|   +-- domain/
|   +-- infrastructure/
|   +-- presentation/
|
+-- tests/
+-- docs/
+-- screenshots/
+-- config/
+-- data/
|
+-- app.py
+-- requirements.txt
+-- README.md
+-- .env.example
+-- .gitignore
+-- Dockerfile
+-- pytest.ini
```

See [Project Structure Documentation](docs/PROJECT_STRUCTURE.md) for more details.

## Installation

### Prerequisites
- Python 3.11
- Git
- pip
- Ollama, if using local AI models

### 1. Clone the Repository

```bash
git clone https://github.com/satya66123/AI-Codebase-Intelligence-Platform.git

cd AI-Codebase-Intelligence-Platform
```

### 2. Create a Virtual Environment

Windows PowerShell:

```powershell
python -m venv .venv

.\.venv\Scripts\Activate.ps1
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Create a `.env` file using `.env.example` as a reference.

Add the API credentials required for the cloud providers you intend to use.

Keep API keys private. Do not commit `.env` files or secrets to GitHub.

### 5. Start the Application

```bash
streamlit run app.py
```

Open the local URL displayed in the terminal.

See the [Installation Guide](docs/INSTALLATION_GUIDE.md) and [User Guide](docs/USER_GUIDE.md) for further instructions.

## Running Tests

Run the complete test suite:

```bash
pytest
```

Run tests with verbose output:

```bash
pytest -v
```

### Final Test Results

| Metric | Result |
|---|---:|
| Total Tests | 3,147 |
| Passed | 3,147 |
| Failed | 0 |
| Pass Rate | 100% |

These are the final test results recorded for the project.

See [Testing Documentation](docs/TESTING_DOCUMENTATION.md).

## Documentation Index

The following documentation files provide additional information about the platform.

### Architecture and Design
- [Architecture](docs/ARCHITECTURE.md)
- [System Design](docs/systemdesign.md)
- [Data Flow](docs/DATA_FLOW_DOCUMENTATION.md)
- [Project Structure](docs/PROJECT_STRUCTURE.md)

### User and Developer Guides
- [User Guide](docs/USER_GUIDE.md)
- [Installation Guide](docs/INSTALLATION_GUIDE.md)
- [Configuration Guide](docs/CONFIGURATION_GUIDE.md)
- [Development Workflow](docs/DEVELOPMENT_WORKFLOW.md)
- [Contributing Guide](docs/CONTRIBUTING.md)
- [Maintenance Guide](docs/MAINTENANCE_GUIDE.md)

### Technical Documentation
- [API Documentation](docs/API_DOCUMENTATION.md)
- [API Reference](docs/API_REFERENCE.md)
- [Features Documentation](docs/FEATURES_DOCUMENTATION.md)
- [AI Provider Documentation](docs/AI_PROVIDER_DOCUMENTATION.md)
- [Repository Discovery Documentation](docs/REPOSITORY_DISCOVERY_DOCUMENTATION.md)
- [Code Quality Documentation](docs/CODE_QUALITY_DOCUMENTATION.md)
- [Application Container Documentation](docs/APPLICATION_CONTAINER_DOCUMENTATION.md)
- [Error Handling Documentation](docs/ERROR_HANDLING_DOCUMENTATION.md)
- [Security Documentation](docs/SECURITY_DOCUMENTATION.md)
- [Dependency Documentation](docs/DEPENDENCY_DOCUMENTATION.md)
- [Logging and Monitoring](docs/LOGGING_AND_MONITORING_DOCUMENTATION.md)
- [Performance Optimization](docs/PERFORMANCE_OPTIMIZATION_DOCUMENTATION.md)

### Testing, Deployment and Release
- [Testing Documentation](docs/TESTING_DOCUMENTATION.md)
- [Deployment Guide](docs/DEPLOYMENT_GUIDE.md)
- [Changelog](docs/CHANGELOG.md)
- [Release Notes](docs/releasenotes.md)
- [License Documentation](docs/LICENSE.md)
- [MIT License](LICENSE)

### Project Planning and Reference
- [Project Summary](docs/PROJECT_SUMMARY.md)
- [Project Notes](docs/projectnotes.md)
- [Project Planner](docs/planner.md)
- [Development Steps](docs/steps.md)
- [FAQ](docs/FAQ.md)
- [Known Limitations](docs/KNOWN_LIMITATIONS.md)
- [Future Enhancements](docs/FUTURE_ENHANCEMENTS.md)
- [Future Improvements](docs/future_improvements.md)
- [Glossary](docs/GLOSSARY.md)
- [Screenshots Documentation](docs/screenshots.md)
- [Documentation Index](docs/documentation.md)

## Screenshots

Application screenshots and recorded project outputs are maintained in the [`screenshots/`](screenshots/) directory.

See [Screenshots Documentation](docs/screenshots.md) for the screenshot reference list.

## Version and Release Information

**Current Version:** `v1.0.0`

**Release Status:** Current release

The project roadmap identifies the following possible future releases:

- `v1.1.0` — Planned
- `v1.2.0` — Proposed
- `v2.0.0` — Long-term proposal

These are roadmap items, not claims that future releases have already been implemented.

See [Release Notes](docs/releasenotes.md) and [Changelog](docs/CHANGELOG.md).

## Future Enhancements

Potential future improvements include:
- Additional code intelligence capabilities.
- More advanced repository analysis.
- Improvements to AI reasoning and evidence validation.
- Expanded engineering reports.
- Further performance and usability improvements.

See [Future Enhancements](docs/FUTURE_ENHANCEMENTS.md) and [Future Improvements](docs/future_improvements.md).

## License

This project is licensed under the MIT License.

See the [LICENSE](LICENSE) file for details.

## Author

**Satya**

GitHub Repository:

[AI Codebase Intelligence Platform](https://github.com/satya66123/AI-Codebase-Intelligence-Platform)

---

**Project Status: Completed**

**Version: 1.0.0**