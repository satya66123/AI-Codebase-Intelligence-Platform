from dataclasses import dataclass


@dataclass(frozen=True)
class AIModel:
    provider: str
    name: str