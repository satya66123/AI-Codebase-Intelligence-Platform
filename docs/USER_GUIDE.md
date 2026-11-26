# User Guide

![Python](https://img.shields.io/badge/Python-3.11-blue)
![Streamlit](https://img.shields.io/badge/UI-Streamlit-red)
![User Guide](https://img.shields.io/badge/Documentation-User_Guide-informational)
[![GitHub](https://img.shields.io/badge/GitHub-Repository-black?logo=github)](https://github.com/satya66123/AI-Codebase-Intelligence-Platform)

## 1. Introduction

The **AI Codebase Intelligence Platform** helps developers explore and understand software repositories through repository discovery, source-code analysis, code quality inspection, and AI model integrations.

This guide provides an overview of the application's usage.

## 2. Prerequisites

Before launching the application, ensure that you have:

- Python 3.11
- Git
- The project repository cloned locally
- The project's required Python dependencies installed
- Any API credentials required by the AI providers you intend to use
- Ollama installed and running if you intend to use local Ollama models

## 3. Set Up the Environment

Open PowerShell in the project directory.

Activate the virtual environment:

```powershell
.venv\Scripts\Activate.ps1
```

Install the project dependencies if they have not already been installed:

```powershell
pip install -r requirements.txt
```

## 4. Launch the Application

Start the Streamlit application using the project's configured entry-point file:

```powershell
streamlit run <application-entry-point>.py
```

Replace the placeholder with the actual Streamlit entry-point filename in the project.

After startup, open the local URL displayed in the terminal.

## 5. Using the Application

### Repository Discovery

Use the repository discovery functionality to begin exploring a software repository.

The application provides repository discovery integration and source-loading services to support repository-related workflows.

### Source Loading

Load the repository source files required for analysis.

The source-loading workflow provides source files to the relevant application features.

### Code Quality Analysis

Open the code quality feature to inspect the available analysis results.

The code quality interface uses the code quality analysis service to process its inputs and present results.

### AI Provider and Model Selection

The platform supports a multi-provider and multi-model configuration.

The configured provider ecosystem includes:

- Ollama
- OpenAI
- Anthropic
- Google Gemini
- Mistral
- Groq
- Cohere
- DeepSeek

Select an available provider and model through the application's provider/model interface.

For cloud providers, configure the required credentials before using their models. For Ollama, ensure the local service and selected model are available.

## 6. Troubleshooting

### Python or Streamlit Command Not Found

Activate the virtual environment and verify that the dependencies are installed.

### Missing Python Dependencies

Run:

```powershell
pip install -r requirements.txt
```

### AI Provider Connection Problems

Check the provider configuration, credentials, network connection, and selected model availability.

For Ollama, verify that the local Ollama service is running and that the selected model is installed.

### Application Startup Problems

Review the terminal output for the relevant Python exception or missing configuration. Resolve the reported issue before restarting the application.

## 7. Usage Recommendations

- Start with the repository discovery workflow.
- Load the source files required for the intended analysis.
- Review the code quality results.
- Choose an AI provider and model that are available in your environment.
- Keep API credentials secure and do not commit secrets to the repository.

## 8. Related Documentation

Refer to the following project documents for additional information:

- `README.md` — Project overview and setup
- `API_DOCUMENTATION.md` — Application interfaces and service methods
- `ARCHITECTURE.md` — High-level architecture

---

![Project Status](https://img.shields.io/badge/Project_Status-Completed-brightgreen)
