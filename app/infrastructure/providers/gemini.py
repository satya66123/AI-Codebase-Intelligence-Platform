from app.config.models import PROVIDER_MODELS
from app.domain.interfaces.ai_provider import AIProvider
from app.infrastructure.providers.gemini_client import GeminiClient


class GeminiProvider(AIProvider):
    def __init__(
        self,
        client: GeminiClient | None = None,
    ) -> None:
        self._client = client or GeminiClient()
        self._models = [
            model.name
            for model in PROVIDER_MODELS["gemini"]
        ]

    @property
    def name(self) -> str:
        return "gemini"

    def generate(self, model: str, prompt: str) -> str:
        if model not in self._models:
            raise ValueError(
                f"Unsupported Gemini model: {model}"
            )

        return self._client.generate(model, prompt)

    def get_models(self) -> list[str]:
        return self._models.copy()