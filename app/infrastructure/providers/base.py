from app.domain.interfaces.ai_provider import AIProvider


class BaseAIProvider(AIProvider):
    def __init__(self, models: list[str]) -> None:
        self._models = models

    def get_models(self) -> list[str]:
        return self._models.copy()