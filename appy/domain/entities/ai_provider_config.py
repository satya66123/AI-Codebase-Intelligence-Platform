from dataclasses import dataclass

from .ai_model import AIModel


@dataclass(frozen=True)
class AIProviderConfig:
    name: str
    models: tuple[AIModel, ...]