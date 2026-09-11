from app.config.models import PROVIDER_MODELS
from app.domain.interfaces.ai_provider import AIProvider
from app.infrastructure.providers.ollama_client import OllamaClient


class OllamaProvider(AIProvider):
    def __init__(
        self,
        client: OllamaClient | None = None,
    ) -> None:
        self._client = client or OllamaClient()
        self._models = [
            model.name
            for model in PROVIDER_MODELS["ollama"]
        ]

    @property
    def name(self) -> str:
        return "ollama"

    def generate(
        self,
        model: str,
        prompt: str,
    ) -> str:
        if model not in self._models:
            raise ValueError(
                f"Unsupported Ollama model: {model}"
            )

        return self._client.generate(
            model=model,
            prompt=prompt,
        )

    def get_models(self) -> list[str]:
        return self._models.copy()