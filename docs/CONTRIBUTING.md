# Contributing Guidelines

![Python](https://img.shields.io/badge/Python-3.11-blue)
![Framework](https://img.shields.io/badge/Framework-Streamlit-red)
![Contributions](https://img.shields.io/badge/Contributions-Welcome-brightgreen)
[![GitHub](https://img.shields.io/badge/GitHub-Repository-black?logo=github)](https://github.com/satya66123/AI-Codebase-Intelligence-Platform)

## 1. Introduction

Thank you for your interest in contributing to the **AI Codebase Intelligence Platform**.

Contributions should help improve application functionality, code quality, reliability, documentation, and developer experience.

## 2. Development Environment

Before contributing, prepare the development environment.

Requirements:

- Python 3.11
- Git
- Project dependencies
- A Python virtual environment

Create a virtual environment:

```powershell
python -m venv .venv
```

Activate it:

```powershell
.venv\Scripts\Activate.ps1
```

Install dependencies:

```powershell
pip install -r requirements.txt
```

## 3. Repository Setup

Clone the repository:

```powershell
git clone https://github.com/satya66123/AI-Codebase-Intelligence-Platform.git
```

Navigate to the project directory:

```powershell
cd AI-Codebase-Intelligence-Platform
```

## 4. Coding Guidelines

When contributing:

- Follow the existing project organization.
- Use clear and descriptive names.
- Keep functions focused on their responsibilities.
- Avoid unnecessary code duplication.
- Handle errors appropriately.
- Keep presentation responsibilities separate from service operations.
- Preserve existing application functionality.
- Avoid introducing unnecessary dependencies.

## 5. Application Architecture

The project uses an application container and service-oriented organization.

Known application areas include:

- `appy/application/`
- `appy/presentation/`
- Repository discovery services
- Repository source-loading services
- Code quality analysis services
- Provider and model management

New functionality should integrate with the existing application structure.

## 6. AI Provider Contributions

The platform is designed around eight AI providers:

- Ollama
- OpenAI
- Anthropic
- Google Gemini
- Mistral
- Groq
- Cohere
- DeepSeek

When adding or modifying provider integrations:

- Follow the existing provider integration approach.
- Validate provider configuration.
- Verify model availability.
- Protect API credentials.
- Handle provider errors appropriately.
- Avoid disrupting existing provider integrations.

## 7. Testing Requirements

The project uses PyTest.

Run the complete test suite before submitting significant changes:

```powershell
pytest -v
```

Contributors should:

1. Add tests for new functionality.
2. Update tests when behavior changes.
3. Correct relevant test failures.
4. Verify existing functionality.
5. Avoid introducing regressions.

## 8. Git Workflow

Create a feature branch:

```powershell
git checkout -b feature/your-feature-name
```

Review changes:

```powershell
git status
git diff
```

Stage and commit changes:

```powershell
git add .
git commit -m "Add descriptive change message"
```

Push the branch:

```powershell
git push origin feature/your-feature-name
```

Submit a pull request through GitHub when appropriate.

## 9. Documentation Guidelines

Update relevant Markdown documentation when changing:

- Application architecture
- Service interfaces
- User-facing features
- Installation or configuration
- AI provider integrations
- Testing procedures

Documentation should reflect actual implemented behavior.

## 10. Security Guidelines

- Never commit API keys or passwords.
- Do not expose private repository contents.
- Use secure credential-management practices.
- Review dependencies before introducing them.
- Do not include sensitive information in logs or documentation.

## 11. Contribution Checklist

- [ ] Development environment is configured.
- [ ] Changes follow the existing project organization.
- [ ] New functionality has appropriate tests.
- [ ] Relevant tests pass.
- [ ] No credentials or secrets are included.
- [ ] Documentation is updated where necessary.
- [ ] Git changes have been reviewed.

## 12. Conclusion

Contributions should preserve the platform's maintainability, reliability, and multi-provider architecture.

Thank you for helping improve the AI Codebase Intelligence Platform.

---

![Project Status](https://img.shields.io/badge/Project_Status-Completed-brightgreen)
