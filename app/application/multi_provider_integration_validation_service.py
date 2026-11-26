
"""Validate provider registration, instantiation, and model availability."""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any


_DEFAULT_EXPECTED_PROVIDERS = object()


class MultiProviderIntegrationValidationError(ValueError):
    """Raised when multi-provider integration validation cannot run."""

    def __init__(self, message: str, stage: str = "validation") -> None:
        super().__init__(message)
        self.stage = stage


@dataclass(frozen=True)
class ProviderValidationResult:
    """Validation details for one AI provider."""

    provider_name: str
    registered: bool
    instantiated: bool
    model_count: int
    models: tuple[str, ...]
    successful: bool
    errors: tuple[str, ...] = ()


@dataclass(frozen=True)
class MultiProviderIntegrationValidationResult:
    """Aggregated validation result for configured AI providers."""

    expected_provider_count: int
    validated_provider_count: int
    successful_provider_count: int
    failed_provider_count: int
    total_model_count: int
    provider_results: tuple[ProviderValidationResult, ...]

    @property
    def is_successful(self) -> bool:
        return (
            self.failed_provider_count == 0
            and self.validated_provider_count == self.expected_provider_count
        )

    @property
    def failed_providers(self) -> tuple[str, ...]:
        return tuple(
            result.provider_name
            for result in self.provider_results
            if not result.successful
        )

    @property
    def successful_providers(self) -> tuple[str, ...]:
        return tuple(
            result.provider_name
            for result in self.provider_results
            if result.successful
        )


class MultiProviderIntegrationValidationService:
    """Validate the configured multi-provider integration."""

    DEFAULT_EXPECTED_PROVIDERS = (
        "ollama",
        "openai",
        "anthropic",
        "gemini",
        "mistral",
        "groq",
        "cohere",
        "deepseek",
    )

    def __init__(
        self,
        provider_factory: Any,
        expected_providers: Any = _DEFAULT_EXPECTED_PROVIDERS,
        expected_models: Mapping[str, tuple[str, ...]] | None = None,
        expected_total_models: int | None = 30,
    ) -> None:
        if provider_factory is None:
            raise MultiProviderIntegrationValidationError(
                "provider_factory cannot be None.",
                stage="configuration",
            )

        if expected_providers is _DEFAULT_EXPECTED_PROVIDERS:
            providers = self.DEFAULT_EXPECTED_PROVIDERS
        else:
            providers = expected_providers

        if not isinstance(providers, tuple) or not providers:
            raise MultiProviderIntegrationValidationError(
                "expected_providers must be a non-empty tuple.",
                stage="configuration",
            )

        if any(
            not isinstance(name, str) or not name.strip()
            for name in providers
        ):
            raise MultiProviderIntegrationValidationError(
                "expected_providers must contain non-empty provider names.",
                stage="configuration",
            )

        if len(set(providers)) != len(providers):
            raise MultiProviderIntegrationValidationError(
                "expected_providers cannot contain duplicates.",
                stage="configuration",
            )

        if expected_models is not None and not isinstance(expected_models, Mapping):
            raise MultiProviderIntegrationValidationError(
                "expected_models must be a mapping.",
                stage="configuration",
            )

        if expected_total_models is not None and (
            isinstance(expected_total_models, bool)
            or not isinstance(expected_total_models, int)
            or expected_total_models < 0
        ):
            raise MultiProviderIntegrationValidationError(
                "expected_total_models must be a non-negative integer or None.",
                stage="configuration",
            )

        self.provider_factory = provider_factory
        self.expected_providers = providers
        self.expected_models = dict(expected_models or {})
        self.expected_total_models = expected_total_models

    def validate(self) -> MultiProviderIntegrationValidationResult:
        """Validate registration, creation, and model availability."""

        try:
            registered_providers = self.provider_factory.supported_providers()
        except Exception as exc:
            raise MultiProviderIntegrationValidationError(
                f"Unable to retrieve registered providers: {exc}",
                stage="registration",
            ) from exc

        if not isinstance(registered_providers, (tuple, list, set, frozenset)):
            raise MultiProviderIntegrationValidationError(
                "supported_providers() must return a collection of provider names.",
                stage="registration",
            )

        registered_names = set(registered_providers)

        results = tuple(
            self._validate_provider(provider_name, registered_names)
            for provider_name in self.expected_providers
        )

        successful_count = sum(result.successful for result in results)
        failed_count = len(results) - successful_count
        total_models = sum(result.model_count for result in results)

        return MultiProviderIntegrationValidationResult(
            expected_provider_count=len(self.expected_providers),
            validated_provider_count=len(results),
            successful_provider_count=successful_count,
            failed_provider_count=failed_count,
            total_model_count=total_models,
            provider_results=results,
        )

    def _validate_provider(
        self,
        provider_name: str,
        registered_names: set[str],
    ) -> ProviderValidationResult:
        """Validate one provider without stopping other checks."""

        errors: list[str] = []
        registered = provider_name in registered_names
        instantiated = False
        models: tuple[str, ...] = ()

        if not registered:
            errors.append("Provider is not registered.")
        else:
            try:
                provider = self.provider_factory.create(provider_name)

                if provider is None:
                    errors.append("Provider factory returned None.")
                else:
                    instantiated = True
                    models = self._get_provider_models(provider)

                    if not models:
                        errors.append("Provider returned no available models.")

            except Exception as exc:
                errors.append(
                    f"Provider creation or model retrieval failed: {exc}"
                )

        expected_models = self.expected_models.get(provider_name)

        if expected_models is not None and instantiated:
            missing_models = tuple(
                model for model in expected_models if model not in models
            )

            if missing_models:
                errors.append(
                    "Expected models are missing: " + ", ".join(missing_models)
                )

        return ProviderValidationResult(
            provider_name=provider_name,
            registered=registered,
            instantiated=instantiated,
            model_count=len(models),
            models=models,
            successful=not errors,
            errors=tuple(errors),
        )

    @staticmethod
    def _get_provider_models(provider: Any) -> tuple[str, ...]:
        """Read and normalize provider model names."""

        get_models = getattr(provider, "get_models", None)

        if not callable(get_models):
            raise ValueError(
                "Provider does not expose a callable get_models()."
            )

        raw_models = get_models()

        if not isinstance(raw_models, (tuple, list, set, frozenset)):
            raise ValueError(
                "Provider get_models() must return a collection."
            )

        normalized: list[str] = []

        for model in raw_models:
            if isinstance(model, str) and model.strip():
                normalized.append(model.strip())

            elif isinstance(model, Mapping):
                name = model.get("name") or model.get("id")

                if isinstance(name, str) and name.strip():
                    normalized.append(name.strip())
                else:
                    raise ValueError(
                        "Provider returned a model without a valid name."
                    )

            else:
                raise ValueError("Provider returned an invalid model entry.")

        if len(set(normalized)) != len(normalized):
            raise ValueError("Provider returned duplicate model names.")

        return tuple(normalized)
