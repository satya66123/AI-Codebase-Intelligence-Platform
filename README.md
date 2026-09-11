# 🤖 AI Codebase Intelligence Platform

An AI-powered Codebase Intelligence Platform built with a modular,
SOLID-based, multi-provider and multi-model architecture.

The platform is designed to understand software repositories,
analyze source code, extract codebase knowledge, and provide
AI-powered intelligence over the complete codebase.

## Project Status

**Current Phase:** Phase 0 — General Foundation

## Architecture

The platform follows:

* SOLID principles
* Separation of concerns
* Dependency inversion
* Interface-based design
* Modular architecture
* Multi-provider support
* Multi-model support
* Dependency injection
* Service-oriented design
* Extensible AI architecture

## AI Providers

The platform is designed to support multiple AI providers through
a common provider abstraction.

Configured providers:

1. Ollama
2. OpenAI
3. Anthropic
4. Google Gemini
5. Mistral
6. Groq
7. Cohere
8. DeepSeek

## AI Models

The platform uses a centralized provider/model configuration.

### Ollama

* qwen2.5:1.5b
* gemma2:2b
* gemma3:4b
* mistral:latest
* phi3:latest
* qwen3:latest
* llama3.1:latest
* llama3:8b
* deepseek-coder:latest

### OpenAI

* gpt-5-mini
* gpt-4o
* gpt-4o-mini

### Anthropic

* claude-sonnet-4-5
* claude-haiku-4-5
* claude-opus-4-1

### Google Gemini

* gemini-3.6-flash
* gemini-2.5-flash
* gemini-2.5-pro

### Mistral

* mistral-medium-latest
* mistral-large-latest
* mistral-small-latest

### Groq

* llama-3.3-70b-versatile
* llama-3.1-8b-instant
* mixtral-8x7b-32768

### Cohere

* command-a-03-2025
* command-r-plus
* command-r

### DeepSeek

* deepseek-chat
* deepseek-reasoner
* deepseek-v4-flash

## Project Phases

```text
Phase 0 → General Foundation
Phase 1 → Codebase Knowledge Ingestion Process
Phase 2 → Codebase Intelligence & Memory Process
Phase 3 → AI Codebase Interaction Process
Phase 4 → Validation & Advanced Codebase Intelligence
```

## Phase 0 Components

```text
Configuration
Provider Abstraction
Provider Clients
Provider Registry
Model Registry
Provider Factory
Dependency Injection
Application Bootstrap
Streamlit Foundation
Logging
Exception Handling
Testing Foundation
```

## Project Structure

```text
app/
├── application/
├── config/
├── core/
├── domain/
├── infrastructure/
└── presentation/

tests/
├── unit/
└── integration/

docs/
├── architecture.md
└── phase-0.md
```

## Configuration

Create a local `.env` file from `.env.example`.

Never commit `.env` or API keys to source control.

Provider and model configuration is centralized so that AI
provider selection remains independent from the core codebase
intelligence logic.

## Running the Application

Install dependencies:

```bash
pip install -r requirements.txt
```

Start Streamlit:

```bash
streamlit run app.py
```

## Development Principles

Every phase follows:

```text
PLAN
 ↓
DESIGN
 ↓
IMPLEMENT
 ↓
TEST
 ↓
FIX
 ↓
STABILIZE
 ↓
DOCUMENT
 ↓
NEXT PHASE
```

## Core Platform Vision

The Codebase Intelligence Platform will progressively provide:

```text
Codebase
   ↓
Repository Discovery
   ↓
Codebase Ingestion
   ↓
Code Understanding
   ↓
Knowledge Extraction
   ↓
AI Intelligence
   ↓
Codebase Interaction
   ↓
Advanced Codebase Intelligence
```

The goal is to build an AI system capable of understanding a
software codebase as a complete system rather than treating
individual source files as isolated documents.

## License

MIT License

````

### `docs/architecture.md`

```markdown
# Architecture

## Architectural Layers

```text
Presentation
     ↓
Application
     ↓
Domain
     ↓
Infrastructure
````

## Dependency Direction

```text
Presentation → Application → Domain
                         ↓
                  Infrastructure
```

The domain layer depends on abstractions rather than concrete
infrastructure implementations.

## Application Architecture

```text
app.py
  ↓
Application
  ↓
Dependency Injection Container
  ↓
Services / Agents
  ↓
Provider Factory
  ↓
AI Provider
  ↓
AI Model
```

The Streamlit entry point remains thin and does not directly
communicate with individual AI providers.

## Provider Architecture

```text
AIProvider
    ↑
Concrete Provider
    ↓
Provider Client
    ↓
External AI API / Local Model
```

## Provider Factory

```text
ProviderFactory
       │
       ├── Ollama
       ├── OpenAI
       ├── Anthropic
       ├── Google Gemini
       ├── Mistral
       ├── Groq
       ├── Cohere
       └── DeepSeek
```

The Provider Factory is responsible for creating the appropriate
provider implementation.

## SOLID

### Single Responsibility

Components have focused responsibilities.

Examples:

```text
Configuration
    → Application configuration

Provider
    → AI communication

Service
    → Business logic

Agent
    → AI workflow

Presentation
    → UI rendering

Container
    → Dependency management
```

### Open/Closed

New providers, models, services, and intelligence capabilities
can be introduced without modifying unrelated core logic.

### Liskov Substitution

Concrete providers implement the common provider abstraction and
can be substituted wherever the base abstraction is required.

### Interface Segregation

Interfaces remain focused and minimal.

### Dependency Inversion

Higher-level application and domain components depend on
abstractions rather than concrete infrastructure implementations.

## Multi-Provider Architecture

8 AI providers are supported through a common provider abstraction.

## Multi-Model Architecture

AI models are centrally configured and associated with their
respective providers.

Provider and model selection remains independent from the core
codebase intelligence business logic.

## Codebase Intelligence Architecture

The long-term architecture follows:

```text
Repository
    ↓
Repository Discovery
    ↓
File Discovery
    ↓
Code Parsing
    ↓
Code Metadata
    ↓
Knowledge Extraction
    ↓
Knowledge Store
    ↓
Retrieval
    ↓
AI Intelligence
    ↓
Codebase Interaction
```

````

### `docs/phase-0.md`

```markdown
# Phase 0 — General Foundation

## Objective

Establish a clean, modular, SOLID-based foundation for the
AI Codebase Intelligence Platform.

The purpose of Phase 0 is to create the architectural foundation
required for future codebase ingestion, intelligence, memory,
interaction, and advanced analysis capabilities.

## Completed

- Project definition
- Architecture design
- Repository structure
- Configuration foundation
- Provider abstraction
- Provider clients
- Provider registry
- Model registry
- Provider factory
- Dependency injection
- Application bootstrap
- Streamlit foundation
- Logging
- Exception handling
- Testing foundation
- Configuration validation
- Architecture stabilization
- Documentation

## Phase 0 Architecture

```text
Streamlit
    ↓
Presentation
    ↓
Application
    ↓
Dependency Injection Container
    ↓
Services / Agents
    ↓
Provider Factory
    ↓
AI Provider
    ↓
AI Model
````

## Phase 0 Goals

```text
✅ Establish project foundation
✅ Establish clean architecture
✅ Establish SOLID principles
✅ Establish provider abstraction
✅ Establish multi-provider foundation
✅ Establish multi-model foundation
✅ Establish dependency injection
✅ Establish application bootstrap
✅ Establish Streamlit foundation
✅ Establish testing foundation
```

## Status

Phase 0 is completed and ready for Phase 1.

## Next Phase

**Phase 1 — Codebase Knowledge Ingestion Process**

````

## Phase 0 Tracker

```text
✅ 0.1  Project Definition & Architecture
✅ 0.2  Repository Structure
✅ 0.3  Configuration Foundation
✅ 0.4  Multi-Provider / Multi-Model Foundation
✅ 0.5  Provider Abstraction
✅ 0.6  Provider Clients
✅ 0.7  Provider Registry
✅ 0.8  Model Registry
✅ 0.9  Provider Factory
✅ 0.10 Dependency Injection Container
✅ 0.11 Logging + Exception Foundation
✅ 0.12 Configuration Validation
✅ 0.13 Application Bootstrap
✅ 0.14 Streamlit Foundation
✅ 0.15 Testing Foundation
✅ 0.16 Stabilization
✅ 0.17 Documentation
✅ 0.18 Phase 0 Review
✅ 0.19 Phase 0 Complete

➡️ Next → Phase 1: Codebase Knowledge Ingestion Process
````
