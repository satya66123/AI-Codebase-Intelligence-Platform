from app.domain.entities.ai_model import AIModel
from app.domain.interfaces.provider_registry import ProviderRegistry


class ProviderModelService:
    def __init__(self, registry: ProviderRegistry) -> None:
        self._registry = registry

    def get_providers(self) -> tuple[str, ...]:
        return tuple(
            provider.name
            for provider in self._registry.get_providers()
        )

    def get_models(self, provider: str) -> tuple[AIModel, ...]:
        return self._registry.get_models(provider)

    def is_supported_provider(self, provider: str) -> bool:
        try:
            self._registry.get_provider(provider)
            return True
        except ValueError:
            return False

    def is_supported_model(
        self,
        provider: str,
        model: str,
    ) -> bool:
        return any(
            ai_model.name == model
            for ai_model in self.get_models(provider)
        )

    def get_default_model(self, provider: str) -> str:
        models = self.get_models(provider)

        if not models:
            raise ValueError(
                f"No models configured for provider: {provider}"
            )

        return models[0].name