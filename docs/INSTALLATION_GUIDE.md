# Installation Guide

![Python](https://img.shields.io/badge/Python-3.11-blue)
![Streamlit](https://img.shields.io/badge/Framework-Streamlit-red)
![Installation](https://img.shields.io/badge/Documentation-Installation_Guide-informational)
[![GitHub](https://img.shields.io/badge/GitHub-Repository-black?logo=github)](https://github.com/satya66123/AI-Codebase-Intelligence-Platform)

## 1. Overview

This guide explains how to prepare the local environment and install the dependencies required to run the **AI Codebase Intelligence Platform**.

## 2. System Requirements

| Requirement | Version / Details |
|---|---|
| Operating System | Windows, Linux, or macOS |
| Python | 3.11 |
| Git | Installed |
| UI Framework | Streamlit |
| Virtual Environment | Python `venv` |
| AI Providers | Local and cloud providers, as configured |

Additional requirements may depend on the AI provider and models selected.

## 3. Clone the Repository

Open PowerShell or a terminal and run:

```powershell
git clone https://github.com/satya66123/AI-Codebase-Intelligence-Platform.git
```

Navigate to the project directory:

```powershell
cd AI-Codebase-Intelligence-Platform
```

If you already have the repository locally, open its existing project directory instead.

## 4. Create a Virtual Environment

Create a Python virtual environment:

```powershell
python -m venv .venv
```

Activate it in Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

For Command Prompt:

```cmd
.venv\Scripts\activate.bat
```

## 5. Install Dependencies

Upgrade pip:

```powershell
python -m pip install --upgrade pip
```

Install the project dependencies:

```powershell
pip install -r requirements.txt
```

## 6. Configure AI Providers

The platform is designed to support these providers:

- Ollama
- OpenAI
- Anthropic
- Google Gemini
- Mistral
- Groq
- Cohere
- DeepSeek

Configure the credentials required by the cloud providers you intend to use, following the project's configuration conventions.

Do not commit API keys, passwords, or other secrets to Git.

### Ollama Setup

If you intend to use local Ollama models:

1. Install Ollama.
2. Start the Ollama service.
3. Download the model you intend to use.
4. Confirm that the model is available locally.
5. Select the model in the application.

Example command:

```powershell
ollama pull qwen2.5:1.5b
```

The model must be installed locally before it can be used.

## 7. Launch the Application

Run the Streamlit application using the actual entry-point file configured in the repository:

```powershell
streamlit run <application-entry-point>.py
```

Replace the placeholder with the correct filename.

Streamlit will display the local application URL in the terminal.

## 8. Verify the Installation

After launching the application, check that:

- The Streamlit interface loads successfully.
- The application pages are accessible.
- Repository discovery functionality is available.
- Source loading works for the intended repository.
- Code quality analysis can be opened.
- Configured AI providers and models are available as expected.

## 9. Common Installation Issues

| Issue | Suggested action |
|---|---|
| Python not recognized | Check the Python installation and PATH |
| Virtual environment activation fails | Check the activation command and PowerShell permissions |
| Missing dependency | Run `pip install -r requirements.txt` |
| Streamlit command not found | Activate the virtual environment and verify Streamlit installation |
| Provider authentication fails | Check the provider credentials and configuration |
| Ollama model unavailable | Pull the model and verify its local availability |
| Application startup error | Review the terminal traceback and correct the reported issue |

## 10. Security Recommendations

- Keep provider API keys private.
- Use environment variables or the project's supported secret-management mechanism.
- Avoid committing local credentials.
- Do not expose sensitive repository contents unintentionally.
- Keep project dependencies updated when appropriate.

---

![Project Status](https://img.shields.io/badge/Project_Status-Completed-brightgreen)
