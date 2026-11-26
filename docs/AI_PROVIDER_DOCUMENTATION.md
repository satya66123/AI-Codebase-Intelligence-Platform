# AI Provider Documentation

![Python](https://img.shields.io/badge/Python-3.11-blue)
![AI](https://img.shields.io/badge/AI-Multi--Provider-informational)
![Providers](https://img.shields.io/badge/Providers-8-success)
![Models](https://img.shields.io/badge/Configured_Models-30-blue)
[![GitHub](https://img.shields.io/badge/GitHub-Repository-black?logo=github)](https://github.com/satya66123/AI-Codebase-Intelligence-Platform)

## 1. Overview

The **AI Codebase Intelligence Platform** uses a multi-provider, multi-model architecture.

It is designed to integrate eight AI providers and support a configured collection of 30 models.

This approach avoids dependence on a single AI provider and gives the application flexibility when selecting models for AI-powered workflows.

## 2. Supported AI Providers

The platform's configured provider ecosystem includes:

| No. | Provider | Execution Type |
|---:|---|---|
| 1 | Ollama | Local |
| 2 | OpenAI | Cloud |
| 3 | Anthropic | Cloud |
| 4 | Google Gemini | Cloud |
| 5 | Mistral | Cloud |
| 6 | Groq | Cloud |
| 7 | Cohere | Cloud |
| 8 | DeepSeek | Cloud |

## 3. Configured Model Groups

### Ollama — Local Models

The configured Ollama model list contains:

1. `qwen2.5:1.5b`
2. `gemma2:2b`
3. `gemma3:4b`
4. `mistral:latest`
5. `phi3:latest`
6. `qwen3:latest`
7. `llama3.1:latest`
8. `llama3:8b`
9. `deepseek-coder:latest`

The default Ollama model is:

`qwen2.5:1.5b`

### OpenAI

Configured models:

- `gpt-5-mini`
- `gpt-4o`
- `gpt-4o-mini`

### Anthropic

Configured models:

- `claude-sonnet-4-5`
- `claude-haiku-4-5`
- `claude-opus-4-1`

### Google Gemini

Configured models:

- `gemini-3.6-flash`
- `gemini-2.5-flash`
- `gemini-2.5-pro`

### Mistral, Groq, Cohere, and DeepSeek

The configuration includes three models for each of these providers.

The exact model identifiers for these four provider groups are not reproduced here because they have not been confirmed in the available documentation context. Refer to the application's model configuration for their exact names.

## 4. Provider and Model Management

The platform uses a provider model service to retrieve provider and model information.

Known service methods include:

```python
get_providers()
get_models(provider)
```

- `get_providers()` retrieves the configured provider list.
- `get_models(provider)` retrieves the models associated with a selected provider.

The application container creates the provider model service through:

```python
create_provider_model_service()
```

## 5. Local and Cloud Model Execution

### Local Execution

Ollama provides local model execution.

Benefits include:

- Running supported models on local infrastructure.
- Reducing dependence on external AI APIs.
- Keeping model execution within the local environment.

Local execution requires Ollama to be installed, running, and configured with the selected model.

### Cloud Execution

The cloud providers offer access to their hosted models through their respective integrations.

Cloud execution requires:

- Valid provider credentials.
- Network connectivity.
- A supported model identifier.
- Provider service availability.

## 6. Provider Selection Workflow

The general provider selection workflow is:

1. Retrieve the configured providers.
2. Display the available providers.
3. Select a provider.
4. Retrieve the models associated with that provider.
5. Select an available model.
6. Use the selected provider and model in the relevant AI workflow.

## 7. Configuration and Security

Follow these practices:

- Keep API keys secure.
- Do not hardcode credentials in source files.
- Do not commit secrets to GitHub.
- Configure each provider independently.
- Verify model availability before use.
- Use local Ollama models only when the required local service and model are available.

## 8. Architecture Benefits

The multi-provider design supports:

- Provider flexibility
- Model selection
- Local and cloud execution options
- Reduced dependence on a single AI vendor
- Future provider integration possibilities

## 9. Summary

The platform is designed around eight AI providers and 30 configured models.

Its provider model service supports provider discovery and model retrieval, while the application can use local or cloud-based AI integrations depending on the selected configuration.

---

![Project Status](https://img.shields.io/badge/Project_Status-Completed-brightgreen)
