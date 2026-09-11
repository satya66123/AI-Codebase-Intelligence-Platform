from app.config.providers import PROVIDERS
from app.domain.entities.ai_model import AIModel
from app.domain.entities.ai_provider_config import AIProviderConfig
from app.domain.interfaces.provider_registry import ProviderRegistry


class InMemoryProviderRegistry(ProviderRegistry):
    def __init__(
        self,
        providers: tuple[AIProviderConfig, ...] = PROVIDERS,
    ) -> None:
        self._providers = {
            provider.name.lower(): provider
            for provider in providers
        }

    def get_provider(self, name: str) -> AIProviderConfig:
        key = name.lower()

        if key not in self._providers:
            raise ValueError(f"Unsupported AI provider: {name}")

        return self._providers[key]

    def get_providers(self) -> tuple[AIProviderConfig, ...]:
        return tuple(self._providers.values())

    def get_models(self, provider: str) -> tuple[AIModel, ...]:
        return self.get_provider(provider).models