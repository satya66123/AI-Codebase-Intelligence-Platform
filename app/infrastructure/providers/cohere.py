from app.config.models import PROVIDER_MODELS
from app.domain.interfaces.ai_provider import AIProvider
from app.infrastructure.providers.cohere_client import CohereClient


class CohereProvider(AIProvider):
    def __init__(
        self,
        client: CohereClient | None = None,
    ) -> None:
        self._client = client or CohereClient()
        self._models = [
            model.name
            for model in PROVIDER_MODELS["cohere"]
        ]

    @property
    def name(self) -> str:
        return "cohere"

    def generate(self, model: str, prompt: str) -> str:
        if model not in self._models:
            raise ValueError(
                f"Unsupported Cohere model: {model}"
            )

        return self._client.generate(model, prompt)

    def get_models(self) -> list[str]:
        return self._models.copy()