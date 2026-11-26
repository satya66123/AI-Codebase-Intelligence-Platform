# Dependency Documentation

![Python](https://img.shields.io/badge/Python-3.11-blue)
![Streamlit](https://img.shields.io/badge/Framework-Streamlit-red)
![Testing](https://img.shields.io/badge/Testing-PyTest-orange)
[![GitHub](https://img.shields.io/badge/GitHub-Repository-black?logo=github)](https://github.com/satya66123/AI-Codebase-Intelligence-Platform)

## 1. Overview

The **AI Codebase Intelligence Platform** uses Python, Streamlit, PyTest, and multiple AI provider integrations.

Its dependencies support the application interface, repository workflows, code analysis, automated testing, and AI model connectivity.

## 2. Core Technology Stack

| Technology | Purpose |
|---|---|
| Python 3.11 | Primary programming language |
| Streamlit | Application user interface |
| PyTest | Automated testing |
| Git | Version control |
| Ollama | Local AI model integration |
| Cloud AI APIs | External AI provider integrations |

## 3. Python Environment

The project uses Python 3.11.

A virtual environment is recommended to isolate project dependencies.

Create the environment:

```powershell
python -m venv .venv
```

Activate it:

```powershell
.venv\Scripts\Activate.ps1
```

## 4. Dependency Installation

The project uses `requirements.txt` to manage Python package dependencies.

Install the configured dependencies:

```powershell
pip install -r requirements.txt
```

Upgrade pip when necessary:

```powershell
python -m pip install --upgrade pip
```

## 5. Application Framework Dependencies

### Streamlit

Streamlit provides the application's user interface and presentation workflow.

### Python Application Modules

The application uses its own modules and services for:

- Application coordination
- Repository discovery
- Repository source loading
- Code quality analysis
- Provider and model management

These application modules are maintained within the project rather than installed as separate third-party packages.

## 6. Testing Dependencies

PyTest is used for automated testing.

Run the complete test suite:

```powershell
pytest -v
```

The project testing work has been completed, and the user has confirmed that the application and tests are working.

## 7. AI Provider Dependencies

The platform is designed to integrate eight AI providers:

| Provider | Integration |
|---|---|
| Ollama | Local model integration |
| OpenAI | Cloud AI integration |
| Anthropic | Cloud AI integration |
| Google Gemini | Cloud AI integration |
| Mistral | Cloud AI integration |
| Groq | Cloud AI integration |
| Cohere | Cloud AI integration |
| DeepSeek | Cloud AI integration |

Each provider may require its own SDK, API client, or compatible integration mechanism.

The exact package names and versions should be taken from the current `requirements.txt` file.

## 8. Dependency Verification

To inspect installed packages:

```powershell
pip list
```

To display dependency information:

```powershell
pip freeze
```

To verify the Python version:

```powershell
python --version
```

## 9. Dependency Maintenance

Recommended practices:

- Keep dependencies recorded in `requirements.txt`.
- Use a virtual environment.
- Review package updates before applying them.
- Avoid unnecessary dependencies.
- Validate application functionality after dependency changes.
- Run the relevant automated tests after updates.

## 10. Important Note

This document describes the known technology stack and dependency categories. It does not invent exact package versions or claim that every provider uses a particular SDK.

For the authoritative package inventory, refer to the repository's current `requirements.txt`.

---

![Project Status](https://img.shields.io/badge/Project_Status-Completed-brightgreen)
