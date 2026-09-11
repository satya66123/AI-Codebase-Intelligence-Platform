from dataclasses import dataclass
import os

from dotenv import load_dotenv

from app.config.constants import (
    APP_NAME,
    APP_VERSION,
    DEFAULT_CAPTION_LANGUAGE,
    DEFAULT_CLOUD_TIMEOUT,
    DEFAULT_DEBUG,
    DEFAULT_ENVIRONMENT,
    DEFAULT_OLLAMA_BASE_URL,
    DEFAULT_OLLAMA_TIMEOUT,
    DEFAULT_TRANSLATION_PROVIDER,
)

load_dotenv()


@dataclass(frozen=True)
class Settings:
    app_name: str = APP_NAME
    app_version: str = APP_VERSION

    environment: str = os.getenv(
        "ENVIRONMENT",
        DEFAULT_ENVIRONMENT,
    )

    debug: bool = (
        os.getenv(
            "DEBUG",
            str(DEFAULT_DEBUG),
        ).lower()
        == "true"
    )

    ollama_base_url: str = os.getenv(
        "OLLAMA_BASE_URL",
        DEFAULT_OLLAMA_BASE_URL,
    )

    ollama_timeout: int = int(
        os.getenv(
            "OLLAMA_TIMEOUT",
            str(DEFAULT_OLLAMA_TIMEOUT),
        )
    )

    cloud_timeout: int = int(
        os.getenv(
            "CLOUD_TIMEOUT",
            str(DEFAULT_CLOUD_TIMEOUT),
        )
    )

    default_translation_provider: str = os.getenv(
        "DEFAULT_TRANSLATION_PROVIDER",
        DEFAULT_TRANSLATION_PROVIDER,
    )

    default_caption_language: str = os.getenv(
        "DEFAULT_CAPTION_LANGUAGE",
        DEFAULT_CAPTION_LANGUAGE,
    )

    ollama_translation_model: str = os.getenv(
        "OLLAMA_TRANSLATION_MODEL",
        "qwen2.5:1.5b",
    )

    openai_translation_model: str = os.getenv(
        "OPENAI_TRANSLATION_MODEL",
        "gpt-5-mini",
    )

    anthropic_translation_model: str = os.getenv(
        "ANTHROPIC_TRANSLATION_MODEL",
        "claude-sonnet-4-5",
    )

    gemini_translation_model: str = os.getenv(
        "GEMINI_TRANSLATION_MODEL",
        "gemini-3.6-flash",
    )

    mistral_translation_model: str = os.getenv(
        "MISTRAL_TRANSLATION_MODEL",
        "mistral-medium-latest",
    )

    groq_translation_model: str = os.getenv(
        "GROQ_TRANSLATION_MODEL",
        "llama-3.1-8b-instant",
    )

    cohere_translation_model: str = os.getenv(
        "COHERE_TRANSLATION_MODEL",
        "command-a-03-2025",
    )

    deepseek_translation_model: str = os.getenv(
        "DEEPSEEK_TRANSLATION_MODEL",
        "deepseek-v4-flash",
    )

    openai_api_key: str = os.getenv(
        "OPENAI_API_KEY",
        "",
    )

    anthropic_api_key: str = os.getenv(
        "ANTHROPIC_API_KEY",
        "",
    )

    gemini_api_key: str = os.getenv(
        "GEMINI_API_KEY",
        "",
    )

    mistral_api_key: str = os.getenv(
        "MISTRAL_API_KEY",
        "",
    )

    groq_api_key: str = os.getenv(
        "GROQ_API_KEY",
        "",
    )

    cohere_api_key: str = os.getenv(
        "COHERE_API_KEY",
        "",
    )

    deepseek_api_key: str = os.getenv(
        "DEEPSEEK_API_KEY",
        "",
    )


settings = Settings()