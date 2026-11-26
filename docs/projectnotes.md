# AI Codebase Intelligence Platform — Project Notes

![Python](https://img.shields.io/badge/Python-3.11-blue)
![Streamlit](https://img.shields.io/badge/UI-Streamlit-red)
![Tests](https://img.shields.io/badge/Tests-3147%20Passed-brightgreen)

## 1. Project Overview

The **AI Codebase Intelligence Platform** is an AI-powered application designed to help developers explore, understand, analyze, and obtain engineering insights from software repositories.

The platform combines repository discovery, code structure analysis, dependency understanding, AI-powered question answering, and advanced code intelligence.

**Repository:** [AI Codebase Intelligence Platform](https://github.com/satya66123/AI-Codebase-Intelligence-Platform)

## 2. Technology Stack

| Area | Technology |
|---|---|
| Programming language | Python |
| User interface | Streamlit |
| Testing | PyTest |
| AI integration | Multiple AI providers |
| Local AI runtime | Ollama |
| Metadata storage | JSON-based storage |
| Version control | Git and GitHub |
| CI | GitHub Actions |
| Media / deployment support | Docker configuration |

## 3. AI Provider Architecture

The platform is designed to support eight AI providers and 30 configured models.

The supported provider list is:

1. Ollama
2. OpenAI
3. Anthropic
4. Google Gemini
5. Mistral
6. Groq
7. Cohere
8. DeepSeek

The configured Ollama models include:

- `qwen2.5:1.5b`
- `gemma2:2b`
- `gemma3:4b`
- `mistral:latest`
- `phi3:latest`
- `qwen3:latest`
- `llama3.1:latest`
- `llama3:8b`
- `deepseek-coder:latest`

The configured OpenAI models include `gpt-5-mini`, `gpt-4o`, and `gpt-4o-mini`.

The configured Anthropic models include `claude-sonnet-4-5`, `claude-haiku-4-5`, and `claude-opus-4-1`.

The configured Gemini models include `gemini-3.6-flash`, `gemini-2.5-flash`, and `gemini-2.5-pro`.

The remaining provider configurations are part of the 30-model configuration. Refer to the application's provider and model configuration for their exact identifiers.

## 4. Locked Development Phases

```text
Phase 0 → General Foundation
   ↓
Phase 1 → Repository Discovery Process
   ↓
Phase 2 → Code Understanding Process
   ↓
Phase 3 → AI Codebase Intelligence Process
   ↓
Phase 4 → Advanced Code Intelligence Process
   ↓
PROJECT COMPLETE
```

### Phase 0 — General Foundation

Established the project foundation, application setup, configuration, provider integration, UI skeleton, testing environment, and development infrastructure.

### Phase 1 — Repository Discovery Process

Focused on repository input, validation, scanning, file discovery, ignore rules, language detection, metadata extraction, repository mapping, and indexing.

### Phase 2 — Code Understanding Process

Focused on AST-based parsing, code entity extraction, imports, dependencies, function calls, inheritance, entry points, and code relationships.

### Phase 3 — AI Codebase Intelligence Process

Focused on natural-language repository interaction, intent detection, relevant code retrieval, context construction, AI reasoning, evidence validation, and source-grounded answers.

### Phase 4 — Advanced Code Intelligence Process

Focused on code quality intelligence, dependency risks, architecture analysis, change impact, technical debt, repository health, and engineering reports.

## 5. Development Rules

- Complete development phases sequentially.
- Test and stabilize each phase before moving to the next.
- Preserve the multi-provider and multi-model architecture.
- Keep repository analysis grounded in discovered source code and metadata.
- Avoid presenting unsupported AI conclusions as verified facts.
- Keep documentation aligned with the actual implementation.
- Phase 0 established the SOLID-based foundation; SOLID is not a mandatory requirement for Phases 1–4.

## 6. Final Testing Result

| Metric | Result |
|---|---:|
| Total tests | 3,147 |
| Passed | 3,147 |
| Failed | 0 |
| Pass rate | 100% |

Testing framework: **PyTest**

## 7. Project Status

The development flow from Phase 0 through Phase 4 is completed. The final reported test result is 3,147 passed out of 3,147.

**Project Status:** Completed