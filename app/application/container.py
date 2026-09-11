from app.application.services.ai_service import AIService
from app.application.services.provider_factory import ProviderFactory
from app.application.services.provider_model_service import (
    ProviderModelService,
)
from app.infrastructure.providers import (
    AnthropicProvider,
    CohereProvider,
    DeepSeekProvider,
    GeminiProvider,
    GroqProvider,
    MistralProvider,
    OllamaProvider,
    OpenAIProvider,
)
from app.infrastructure.providers.registry import (
    InMemoryProviderRegistry,
)


class ApplicationContainer:
    def __init__(self) -> None:
        self._provider_registry = InMemoryProviderRegistry()

        self._provider_factory = ProviderFactory()

        self._register_providers()

    def _register_providers(self) -> None:
        self._provider_factory.register(
            "ollama",
            OllamaProvider,
        )
        self._provider_factory.register(
            "openai",
            OpenAIProvider,
        )
        self._provider_factory.register(
            "anthropic",
            AnthropicProvider,
        )
        self._provider_factory.register(
            "gemini",
            GeminiProvider,
        )
        self._provider_factory.register(
            "mistral",
            MistralProvider,
        )
        self._provider_factory.register(
            "groq",
            GroqProvider,
        )
        self._provider_factory.register(
            "cohere",
            CohereProvider,
        )
        self._provider_factory.register(
            "deepseek",
            DeepSeekProvider,
        )

    @property
    def provider_registry(self) -> InMemoryProviderRegistry:
        return self._provider_registry

    @property
    def provider_factory(self) -> ProviderFactory:
        return self._provider_factory

    def create_provider_model_service(
        self,
    ) -> ProviderModelService:
        return ProviderModelService(
            registry=self._provider_registry,
        )

    def create_ai_service(
        self,
        provider_name: str,
    ) -> AIService:
        provider = self._provider_factory.create(
            provider_name,
        )

        return AIService(
            provider=provider,
        )