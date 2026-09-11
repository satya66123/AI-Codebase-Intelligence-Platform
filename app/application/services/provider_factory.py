from collections.abc import Callable

from app.domain.interfaces.ai_provider import AIProvider


ProviderBuilder = Callable[[], AIProvider]


class ProviderFactory:
    def __init__(
        self,
        providers: dict[str, ProviderBuilder] | None = None,
    ) -> None:
        self._providers: dict[str, ProviderBuilder] = (
            providers.copy() if providers else {}
        )

    def register(
        self,
        name: str,
        builder: ProviderBuilder,
    ) -> None:
        key = name.strip().lower()

        if not key:
            raise ValueError("Provider name cannot be empty.")

        self._providers[key] = builder

    def create(self, provider_name: str) -> AIProvider:
        key = provider_name.strip().lower()

        builder = self._providers.get(key)

        if builder is None:
            raise ValueError(
                f"Unsupported AI provider: {provider_name}"
            )

        return builder()

    def supported_providers(self) -> tuple[str, ...]:
        return tuple(self._providers.keys())