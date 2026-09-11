from app.config.models import PROVIDER_MODELS
from app.domain.interfaces.ai_provider import AIProvider
from app.infrastructure.providers.mistral_client import MistralClient


class MistralProvider(AIProvider):
    def __init__(
        self,
        client: MistralClient | None = None,
    ) -> None:
        self._client = client or MistralClient()
        self._models = [
            model.name
            for model in PROVIDER_MODELS["mistral"]
        ]

    @property
    def name(self) -> str:
        return "mistral"

    def generate(self, model: str, prompt: str) -> str:
        if model not in self._models:
            raise ValueError(
                f"Unsupported Mistral model: {model}"
            )

        return self._client.generate(model, prompt)

    def get_models(self) -> list[str]:
        return self._models.copy()