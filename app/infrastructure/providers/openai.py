from app.config.models import PROVIDER_MODELS
from app.domain.interfaces.ai_provider import AIProvider
from app.infrastructure.providers.openai_client import OpenAIClient


class OpenAIProvider(AIProvider):
    def __init__(
        self,
        client: OpenAIClient | None = None,
    ) -> None:
        self._client = client or OpenAIClient()
        self._models = [
            model.name
            for model in PROVIDER_MODELS["openai"]
        ]

    @property
    def name(self) -> str:
        return "openai"

    def generate(
        self,
        model: str,
        prompt: str,
    ) -> str:
        if model not in self._models:
            raise ValueError(
                f"Unsupported OpenAI model: {model}"
            )

        return self._client.generate(
            model,
            prompt,
        )

    def get_models(self) -> list[str]:
        return self._models.copy()