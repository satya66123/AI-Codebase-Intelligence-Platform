from app.domain.entities.ai_model import AIModel


PROVIDER_MODELS: dict[str, tuple[AIModel, ...]] = {
    "ollama": (
        AIModel("ollama", "qwen2.5:1.5b"),
        AIModel("ollama", "gemma2:2b"),
        AIModel("ollama", "gemma3:4b"),
        AIModel("ollama", "mistral:latest"),
        AIModel("ollama", "phi3:latest"),
        AIModel("ollama", "qwen3:latest"),
        AIModel("ollama", "llama3.1:latest"),
        AIModel("ollama", "llama3:8b"),
        AIModel("ollama", "deepseek-coder:latest"),
    ),
    "openai": (
        AIModel("openai", "gpt-5-mini"),
        AIModel("openai", "gpt-4o"),
        AIModel("openai", "gpt-4o-mini"),
    ),
    "anthropic": (
        AIModel("anthropic", "claude-sonnet-4-5"),
        AIModel("anthropic", "claude-haiku-4-5"),
        AIModel("anthropic", "claude-opus-4-1"),
    ),
    "gemini": (
        AIModel("gemini", "gemini-3.6-flash"),
        AIModel("gemini", "gemini-2.5-flash"),
        AIModel("gemini", "gemini-2.5-pro"),
    ),
    "mistral": (
        AIModel("mistral", "mistral-medium-latest"),
        AIModel("mistral", "mistral-large-latest"),
        AIModel("mistral", "mistral-small-latest"),
    ),
    "groq": (
        AIModel("groq", "llama-3.3-70b-versatile"),
        AIModel("groq", "llama-3.1-8b-instant"),
        AIModel("groq", "mixtral-8x7b-32768"),
    ),
    "cohere": (
        AIModel("cohere", "command-a-03-2025"),
        AIModel("cohere", "command-r-plus"),
        AIModel("cohere", "command-r"),
    ),
    "deepseek": (
        AIModel("deepseek", "deepseek-chat"),
        AIModel("deepseek", "deepseek-reasoner"),
        AIModel("deepseek", "deepseek-v4-flash"),
    ),
}