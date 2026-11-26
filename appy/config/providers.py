from appy.config.models import PROVIDER_MODELS
from appy.domain.entities.ai_provider_config import AIProviderConfig


PROVIDERS: tuple[AIProviderConfig, ...] = tuple(
    AIProviderConfig(
        name=provider,
        models=models,
    )
    for provider, models in PROVIDER_MODELS.items()
)