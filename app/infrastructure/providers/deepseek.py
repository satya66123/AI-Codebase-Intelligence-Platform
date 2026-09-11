from app.config.models import PROVIDER_MODELS
from app.domain.interfaces.ai_provider import AIProvider
from app.infrastructure.providers.deepseek_client import DeepSeekClient


class DeepSeekProvider(AIProvider):
    def __init__(
        self,
        client: DeepSeekClient | None = None,
    ) -> None:
        self._client = client or DeepSeekClient()
        self._models = [
            model.name
            for model in PROVIDER_MODELS["deepseek"]
        ]

    @property
    def name(self) -> str:
        return "deepseek"

    def generate(self, model: str, prompt: str) -> str:
        if model not in self._models:
            raise ValueError(
                f"Unsupported DeepSeek model: {model}"
            )

        return self._client.generate(model, prompt)

    def get_models(self) -> list[str]:
        return self._models.copy()