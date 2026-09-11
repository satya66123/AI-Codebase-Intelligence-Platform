from app.config.models import PROVIDER_MODELS
from app.domain.interfaces.ai_provider import AIProvider
from app.infrastructure.providers.anthropic_client import AnthropicClient


class AnthropicProvider(AIProvider):
    def __init__(
        self,
        client: AnthropicClient | None = None,
    ) -> None:
        self._client = client or AnthropicClient()
        self._models = [
            model.name
            for model in PROVIDER_MODELS["anthropic"]
        ]

    @property
    def name(self) -> str:
        return "anthropic"

    def generate(self, model: str, prompt: str) -> str:
        if model not in self._models:
            raise ValueError(
                f"Unsupported Anthropic model: {model}"
            )

        return self._client.generate(model, prompt)

    def get_models(self) -> list[str]:
        return self._models.copy()