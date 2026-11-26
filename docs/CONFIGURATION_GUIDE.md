# Configuration Guide

![Python](https://img.shields.io/badge/Python-3.11-blue)
![Streamlit](https://img.shields.io/badge/Framework-Streamlit-red)
![AI](https://img.shields.io/badge/AI-Multi--Provider-informational)
[![GitHub](https://img.shields.io/badge/GitHub-Repository-black?logo=github)](https://github.com/satya66123/AI-Codebase-Intelligence-Platform)

## 1. Overview

The **AI Codebase Intelligence Platform** supports a multi-provider and multi-model architecture.

The application is designed to work with local and cloud-based AI providers. Provider and model management is coordinated through the application's provider model service.

## 2. Supported AI Providers

The configured provider ecosystem includes eight providers:

| Provider | Type |
|---|---|
| Ollama | Local |
| OpenAI | Cloud |
| Anthropic | Cloud |
| Google Gemini | Cloud |
| Mistral | Cloud |
| Groq | Cloud |
| Cohere | Cloud |
| DeepSeek | Cloud |

Availability depends on the provider configuration and the models supported by the application.

## 3. Model Configuration

The platform supports selecting models associated with the configured providers.

Model selection should use the models available through the application's provider/model management interface.

The application exposes the following service methods:

- `get_providers()` — retrieves the available providers.
- `get_models(provider)` — retrieves the models associated with a provider.

These methods are part of the provider model service.

## 4. Ollama Configuration

Ollama provides local model execution.

To use Ollama:

1. Install Ollama on the machine.
2. Start the Ollama service.
3. Download the required model.
4. Confirm that the model is available.
5. Select Ollama and the desired model in the application.

Example:

```powershell
ollama pull qwen2.5:1.5b
```

Check locally available models:

```powershell
ollama list
```

The application can use a local model only when the Ollama service and selected model are available.

## 5. Cloud Provider Configuration

Cloud providers generally require API credentials.

Before using a cloud provider:

1. Obtain an API key from the provider.
2. Configure the credential using the application's supported configuration mechanism.
3. Verify that the credential is valid.
4. Select the corresponding provider and model in the application.

Do not assume that one provider's API key can be used with another provider.

## 6. Credential and Secret Management

Follow these security practices:

- Never hardcode API keys in application source code.
- Do not commit API keys or passwords to Git.
- Keep local secret files out of version control.
- Use environment variables or the secret-management mechanism supported by the project.
- Restrict access to credentials.
- Rotate credentials if they are accidentally exposed.

## 7. Configuration Verification

After configuring a provider, verify that:

- The provider appears in the application.
- Its available models can be retrieved.
- The selected model is available.
- Required credentials are configured.
- A provider connection or model operation completes successfully.

For Ollama, also verify that the local service is running and the selected model has been downloaded.

## 8. Troubleshooting

| Problem | What to check |
|---|---|
| Provider not listed | Check provider registration and application configuration |
| Models not displayed | Check model configuration and provider model service |
| Authentication failure | Verify the API key and provider credentials |
| Ollama connection failure | Check whether the Ollama service is running |
| Model not found | Verify that the selected model is available |
| Provider request failure | Review the error message and provider connectivity |

## 9. Implementation Note

This guide documents the platform's provider configuration concepts and known service interfaces. Exact environment-variable names, configuration filenames, and secret-file locations should be taken from the current source code rather than assumed.

---

![Project Status](https://img.shields.io/badge/Project_Status-Completed-brightgreen)
