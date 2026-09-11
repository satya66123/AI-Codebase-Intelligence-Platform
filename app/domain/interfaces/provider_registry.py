from abc import ABC, abstractmethod

from app.domain.entities.ai_model import AIModel
from app.domain.entities.ai_provider_config import AIProviderConfig


class ProviderRegistry(ABC):
    @abstractmethod
    def get_provider(self, name: str) -> AIProviderConfig:
        pass

    @abstractmethod
    def get_providers(self) -> tuple[AIProviderConfig, ...]:
        pass

    @abstractmethod
    def get_models(self, provider: str) -> tuple[AIModel, ...]:
        pass