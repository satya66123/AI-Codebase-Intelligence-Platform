# Frequently Asked Questions (FAQ)

![Python](https://img.shields.io/badge/Python-3.11-blue)
![Framework](https://img.shields.io/badge/Framework-Streamlit-red)
![AI Providers](https://img.shields.io/badge/AI_Providers-8-success)
![License](https://img.shields.io/badge/License-MIT-green)
[![GitHub](https://img.shields.io/badge/GitHub-Repository-black?logo=github)](https://github.com/satya66123/AI-Codebase-Intelligence-Platform)

## 1. General Questions

### What is the AI Codebase Intelligence Platform?

It is an AI-powered application designed to help developers explore and understand software repositories through repository discovery, source-code loading, code quality analysis, and AI provider integrations.

### Which programming language does the project use?

Python 3.11.

### Which framework is used for the user interface?

Streamlit.

### Is the project completed?

Yes. The current project development and testing work has been completed.

### Is the project open source?

The project is released under the MIT License.

## 2. Installation Questions

### What Python version is required?

Python 3.11.

### How do I install project dependencies?

Run:

```powershell
pip install -r requirements.txt
```

### How do I activate the virtual environment?

For Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

### How do I launch the application?

Run Streamlit with the configured application entry-point file:

```powershell
streamlit run <application-entry-point>.py
```

Replace the placeholder with the actual filename.

## 3. Repository Discovery Questions

### What is repository discovery?

Repository discovery is the functionality used to begin exploring a software repository.

### Which service coordinates repository discovery?

The application uses the repository discovery integration service.

### Which service loads repository source files?

The repository source loading service.

### Where is the repository discovery interface?

`appy/presentation/repository_discovery_view.py`

## 4. Code Quality Questions

### Does the platform provide code quality analysis?

Yes. The application includes a dedicated code quality interface and analysis service.

### Where is the code quality interface?

`appy/presentation/code_quality_view.py`

### Which method creates the code quality analysis service?

```python
create_code_quality_analysis_service()
```

### How are source files passed to the code quality view?

The known interface accepts `source_files` and `service` arguments:

```python
render_code_quality_view(
    source_files=source_files,
    service=quality_service
)
```

## 5. AI Provider Questions

### How many AI providers does the platform support?

The configured provider ecosystem contains eight providers.

### Which providers are included?

1. Ollama
2. OpenAI
3. Anthropic
4. Google Gemini
5. Mistral
6. Groq
7. Cohere
8. DeepSeek

### How many models are configured?

The platform's configured collection contains 30 models.

### Does the platform support local AI models?

Yes. Ollama provides local model integration.

### What is the default Ollama model?

`qwen2.5:1.5b`

### Do cloud AI providers require API keys?

Yes. Cloud provider integrations generally require their respective credentials.

## 6. Application Architecture Questions

### What is the application container?

It is the component responsible for creating and providing the application services.

### Where is the application container located?

`appy.application.ApplicationContainer`

### Which service retrieves available AI providers?

The provider model service.

### Which methods retrieve provider and model information?

```python
get_providers()
get_models(provider)
```

## 7. Testing Questions

### Which testing framework is used?

PyTest.

### How do I run the complete test suite?

```powershell
pytest -v
```

### Are the project tests completed?

Yes. The user confirmed that the application and tests are working after the identified test-reference issues were corrected.

### Should tests be run after future code changes?

Yes. Relevant tests should be executed after modifications to help prevent regressions.

## 8. Troubleshooting Questions

### What should I do if the application does not start?

Check the Python environment, installed dependencies, application entry-point filename, and terminal traceback.

### What should I do if an AI provider fails?

Verify provider credentials, connectivity, model availability, and provider configuration.

### What should I do if an Ollama model is unavailable?

Check installed models:

```powershell
ollama list
```

Download the required model if necessary.

### What should I do if a test fails?

Review the PyTest failure output, identify the affected component, correct the issue, and rerun the relevant tests.

## 9. License Questions

### Which license does the project use?

MIT License.

### Who owns the copyright?

satya.

### What is the copyright year?

2026.

### Can the software be modified and distributed?

The MIT License permits use, modification, distribution, sublicensing, and commercial use, subject to its conditions.

## 10. Additional Documentation

Refer to the other project documents for more information:

- `README.md`
- `API_DOCUMENTATION.md`
- `ARCHITECTURE.md`
- `USER_GUIDE.md`
- `INSTALLATION_GUIDE.md`
- `CONFIGURATION_GUIDE.md`
- `AI_PROVIDER_DOCUMENTATION.md`
- `TESTING_DOCUMENTATION.md`
- `DEPLOYMENT_GUIDE.md`

## 11. Conclusion

This FAQ provides a quick reference for common questions about the AI Codebase Intelligence Platform.

For more detailed technical information, refer to the corresponding documentation files.

---

![Project Status](https://img.shields.io/badge/Project_Status-Completed-brightgreen)
