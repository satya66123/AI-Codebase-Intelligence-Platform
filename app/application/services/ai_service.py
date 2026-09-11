from app.domain.interfaces.ai_provider import AIProvider


class AIService:
    def __init__(self, provider: AIProvider) -> None:
        self._provider = provider

    @property
    def provider(self) -> AIProvider:
        return self._provider

    def available_models(self) -> list[str]:
        return self._provider.get_models()

    def generate(self, model: str, prompt: str) -> str:
        return self._provider.generate(model, prompt)