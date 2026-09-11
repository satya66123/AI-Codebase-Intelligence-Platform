from app.config.models import PROVIDER_MODELS
from app.domain.entities.ai_provider_config import AIProviderConfig


PROVIDERS: tuple[AIProviderConfig, ...] = tuple(
    AIProviderConfig(
        name=provider,
        models=models,
    )
    for provider, models in PROVIDER_MODELS.items()
)