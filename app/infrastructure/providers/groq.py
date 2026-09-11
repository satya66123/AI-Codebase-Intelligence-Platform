from app.config.models import PROVIDER_MODELS
from app.domain.interfaces.ai_provider import AIProvider
from app.infrastructure.providers.groq_client import GroqClient


class GroqProvider(AIProvider):
    def __init__(
        self,
        client: GroqClient | None = None,
    ) -> None:
        self._client = client or GroqClient()
        self._models = [
            model.name
            for model in PROVIDER_MODELS["groq"]
        ]

    @property
    def name(self) -> str:
        return "groq"

    def generate(self, model: str, prompt: str) -> str:
        if model not in self._models:
            raise ValueError(
                f"Unsupported Groq model: {model}"
            )

        return self._client.generate(model, prompt)

    def get_models(self) -> list[str]:
        return self._models.copy()