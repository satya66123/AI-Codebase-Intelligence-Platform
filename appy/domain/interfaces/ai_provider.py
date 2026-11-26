from abc import ABC, abstractmethod


class AIProvider(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    def generate(self, model: str, prompt: str) -> str:
        pass

    @abstractmethod
    def get_models(self) -> list[str]:
        pass