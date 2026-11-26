
"""Tests for multi-provider integration validation."""

import pytest

from app.application.multi_provider_integration_validation_service import (
    MultiProviderIntegrationValidationError,
    MultiProviderIntegrationValidationResult,
    MultiProviderIntegrationValidationService,
    ProviderValidationResult,
)


class FakeProvider:
    """Test provider with a configurable model list."""

    def __init__(self, models=None, error=None):
        self.models = models if models is not None else ["model-a", "model-b"]
        self.error = error

    def get_models(self):
        if self.error is not None:
            raise self.error
        return self.models


class FakeProviderFactory:
    """Test provider factory."""

    def __init__(self, providers=None, registered=None, error=None):
        self.providers = providers or {}
        self.registered = (
            list(registered)
            if registered is not None
            else list(self.providers)
        )
        self.error = error
        self.created = []

    def supported_providers(self):
        if self.error is not None:
            raise self.error
        return self.registered

    def create(self, provider_name):
        self.created.append(provider_name)
        provider = self.providers.get(provider_name)

        if provider is None:
            raise ValueError(f"Unknown provider: {provider_name}")

        return provider


@pytest.fixture
def provider_factory():
    providers = {
        name: FakeProvider()
        for name in (
            "ollama",
            "openai",
            "anthropic",
            "gemini",
            "mistral",
            "groq",
            "cohere",
            "deepseek",
        )
    }
    return FakeProviderFactory(providers=providers)


@pytest.fixture
def service(provider_factory):
    return MultiProviderIntegrationValidationService(
        provider_factory=provider_factory
    )


def test_default_expected_providers_contains_eight_providers():
    assert len(
        MultiProviderIntegrationValidationService.DEFAULT_EXPECTED_PROVIDERS
    ) == 8


def test_default_expected_providers_contains_all_configured_providers():
    assert MultiProviderIntegrationValidationService.DEFAULT_EXPECTED_PROVIDERS == (
        "ollama",
        "openai",
        "anthropic",
        "gemini",
        "mistral",
        "groq",
        "cohere",
        "deepseek",
    )


def test_constructor_rejects_none_factory():
    with pytest.raises(MultiProviderIntegrationValidationError) as exc_info:
        MultiProviderIntegrationValidationService(provider_factory=None)

    assert exc_info.value.stage == "configuration"


def test_constructor_accepts_custom_expected_providers():
    factory = FakeProviderFactory(
        providers={"openai": FakeProvider()}
    )
    service = MultiProviderIntegrationValidationService(
        provider_factory=factory,
        expected_providers=("openai",),
    )

    assert service.expected_providers == ("openai",)


@pytest.mark.parametrize("providers", [None, (), [], "openai"])
def test_constructor_rejects_invalid_expected_providers(providers):
    with pytest.raises(MultiProviderIntegrationValidationError):
        MultiProviderIntegrationValidationService(
            provider_factory=FakeProviderFactory(),
            expected_providers=providers,
        )


@pytest.mark.parametrize("providers", [("",), (" ",), (None,), (123,)])
def test_constructor_rejects_invalid_provider_names(providers):
    with pytest.raises(MultiProviderIntegrationValidationError):
        MultiProviderIntegrationValidationService(
            provider_factory=FakeProviderFactory(),
            expected_providers=providers,
        )


def test_constructor_rejects_duplicate_expected_providers():
    with pytest.raises(MultiProviderIntegrationValidationError):
        MultiProviderIntegrationValidationService(
            provider_factory=FakeProviderFactory(),
            expected_providers=("openai", "openai"),
        )


def test_constructor_rejects_non_mapping_expected_models():
    with pytest.raises(MultiProviderIntegrationValidationError):
        MultiProviderIntegrationValidationService(
            provider_factory=FakeProviderFactory(),
            expected_models=("openai",),
        )


@pytest.mark.parametrize("count", [-1, 1.5, True, "30"])
def test_constructor_rejects_invalid_expected_total_models(count):
    with pytest.raises(MultiProviderIntegrationValidationError):
        MultiProviderIntegrationValidationService(
            provider_factory=FakeProviderFactory(),
            expected_total_models=count,
        )


def test_constructor_accepts_none_expected_total_models():
    service = MultiProviderIntegrationValidationService(
        provider_factory=FakeProviderFactory(),
        expected_total_models=None,
    )

    assert service.expected_total_models is None


def test_validate_returns_aggregated_result(service):
    result = service.validate()

    assert isinstance(result, MultiProviderIntegrationValidationResult)


def test_validate_checks_all_eight_providers(service):
    result = service.validate()

    assert result.expected_provider_count == 8
    assert result.validated_provider_count == 8


def test_validate_creates_each_expected_provider(service, provider_factory):
    service.validate()

    assert provider_factory.created == list(service.expected_providers)


def test_validate_reports_all_providers_successful(service):
    result = service.validate()

    assert result.successful_provider_count == 8
    assert result.failed_provider_count == 0
    assert result.is_successful is True


def test_validate_counts_models_across_providers(service):
    result = service.validate()

    assert result.total_model_count == 16


def test_validate_returns_provider_results(service):
    result = service.validate()

    assert len(result.provider_results) == 8
    assert all(
        isinstance(item, ProviderValidationResult)
        for item in result.provider_results
    )


def test_validate_reports_successful_provider_names(service):
    result = service.validate()

    assert result.successful_providers == service.expected_providers
    assert result.failed_providers == ()


def test_validate_detects_unregistered_provider():
    factory = FakeProviderFactory(
        providers={"openai": FakeProvider()},
        registered=("openai",),
    )
    service = MultiProviderIntegrationValidationService(
        provider_factory=factory,
        expected_providers=("openai", "ollama"),
    )

    result = service.validate()

    assert result.failed_provider_count == 1
    assert result.failed_providers == ("ollama",)
    assert "Provider is not registered." in result.provider_results[1].errors


def test_validate_does_not_create_unregistered_provider():
    factory = FakeProviderFactory(
        providers={"openai": FakeProvider()},
        registered=("openai",),
    )
    service = MultiProviderIntegrationValidationService(
        provider_factory=factory,
        expected_providers=("openai", "ollama"),
    )

    service.validate()

    assert factory.created == ["openai"]


def test_validate_detects_provider_creation_failure():
    factory = FakeProviderFactory(
        providers={},
        registered=("openai",),
    )
    service = MultiProviderIntegrationValidationService(
        provider_factory=factory,
        expected_providers=("openai",),
    )

    result = service.validate()

    assert result.failed_provider_count == 1
    assert result.provider_results[0].instantiated is False
    assert "Provider creation or model retrieval failed" in (
        result.provider_results[0].errors[0]
    )


def test_validate_detects_provider_returning_none():
    class NoneProviderFactory:
        def supported_providers(self):
            return ("openai",)

        def create(self, provider_name):
            return None

    service = MultiProviderIntegrationValidationService(
        provider_factory=NoneProviderFactory(),
        expected_providers=("openai",),
    )

    result = service.validate()

    assert result.provider_results[0].instantiated is False
    assert "Provider factory returned None." in result.provider_results[0].errors


def test_validate_detects_model_retrieval_failure():
    factory = FakeProviderFactory(
        providers={
            "openai": FakeProvider(error=RuntimeError("model service unavailable"))
        },
        registered=("openai",),
    )
    service = MultiProviderIntegrationValidationService(
        provider_factory=factory,
        expected_providers=("openai",),
    )

    result = service.validate()

    assert result.failed_provider_count == 1
    assert "model service unavailable" in result.provider_results[0].errors[0]


def test_validate_detects_empty_model_list():
    factory = FakeProviderFactory(
        providers={"openai": FakeProvider(models=[])},
        registered=("openai",),
    )
    service = MultiProviderIntegrationValidationService(
        provider_factory=factory,
        expected_providers=("openai",),
    )

    result = service.validate()

    assert result.provider_results[0].model_count == 0
    assert "Provider returned no available models." in (
        result.provider_results[0].errors
    )


def test_validate_detects_missing_expected_models():
    factory = FakeProviderFactory(
        providers={"openai": FakeProvider(models=["model-a"])},
        registered=("openai",),
    )
    service = MultiProviderIntegrationValidationService(
        provider_factory=factory,
        expected_providers=("openai",),
        expected_models={"openai": ("model-a", "model-b")},
    )

    result = service.validate()

    assert result.failed_provider_count == 1
    assert "Expected models are missing: model-b" in (
        result.provider_results[0].errors
    )


def test_validate_accepts_all_expected_models():
    factory = FakeProviderFactory(
        providers={"openai": FakeProvider(models=["model-a", "model-b"])},
        registered=("openai",),
    )
    service = MultiProviderIntegrationValidationService(
        provider_factory=factory,
        expected_providers=("openai",),
        expected_models={"openai": ("model-a", "model-b")},
    )

    result = service.validate()

    assert result.is_successful is True


def test_validate_normalizes_model_mapping_entries():
    factory = FakeProviderFactory(
        providers={
            "openai": FakeProvider(
                models=[{"name": "model-a"}, {"id": "model-b"}]
            )
        },
        registered=("openai",),
    )
    service = MultiProviderIntegrationValidationService(
        provider_factory=factory,
        expected_providers=("openai",),
    )

    result = service.validate()

    assert result.provider_results[0].models == ("model-a", "model-b")


def test_validate_rejects_model_entry_without_name():
    factory = FakeProviderFactory(
        providers={"openai": FakeProvider(models=[{"version": "1"}])},
        registered=("openai",),
    )
    service = MultiProviderIntegrationValidationService(
        provider_factory=factory,
        expected_providers=("openai",),
    )

    result = service.validate()

    assert result.failed_provider_count == 1
    assert "valid name" in result.provider_results[0].errors[0]


def test_validate_rejects_duplicate_model_names():
    factory = FakeProviderFactory(
        providers={"openai": FakeProvider(models=["model-a", "model-a"])},
        registered=("openai",),
    )
    service = MultiProviderIntegrationValidationService(
        provider_factory=factory,
        expected_providers=("openai",),
    )

    result = service.validate()

    assert result.failed_provider_count == 1
    assert "duplicate model names" in result.provider_results[0].errors[0]


def test_validate_rejects_invalid_model_collection():
    factory = FakeProviderFactory(
        providers={"openai": FakeProvider(models="model-a")},
        registered=("openai",),
    )
    service = MultiProviderIntegrationValidationService(
        provider_factory=factory,
        expected_providers=("openai",),
    )

    result = service.validate()

    assert result.failed_provider_count == 1
    assert "must return a collection" in result.provider_results[0].errors[0]


def test_validate_continues_after_one_provider_fails():
    factory = FakeProviderFactory(
        providers={
            "openai": FakeProvider(error=RuntimeError("failed")),
            "ollama": FakeProvider(models=["qwen2.5:1.5b"]),
        },
        registered=("openai", "ollama"),
    )
    service = MultiProviderIntegrationValidationService(
        provider_factory=factory,
        expected_providers=("openai", "ollama"),
    )

    result = service.validate()

    assert result.validated_provider_count == 2
    assert result.successful_provider_count == 1
    assert result.failed_provider_count == 1


def test_validate_wraps_registration_failure():
    factory = FakeProviderFactory(error=RuntimeError("registry unavailable"))
    service = MultiProviderIntegrationValidationService(
        provider_factory=factory,
    )

    with pytest.raises(MultiProviderIntegrationValidationError) as exc_info:
        service.validate()

    assert exc_info.value.stage == "registration"
    assert "registry unavailable" in str(exc_info.value)


def test_validate_rejects_invalid_registered_provider_collection():
    class InvalidFactory:
        def supported_providers(self):
            return "openai"

    service = MultiProviderIntegrationValidationService(
        provider_factory=InvalidFactory(),
        expected_providers=("openai",),
    )

    with pytest.raises(MultiProviderIntegrationValidationError) as exc_info:
        service.validate()

    assert exc_info.value.stage == "registration"


def test_custom_provider_set_can_be_validated():
    factory = FakeProviderFactory(
        providers={"custom": FakeProvider()},
        registered=("custom",),
    )
    service = MultiProviderIntegrationValidationService(
        provider_factory=factory,
        expected_providers=("custom",),
        expected_total_models=None,
    )

    result = service.validate()

    assert result.is_successful is True
    assert result.successful_providers == ("custom",)


def test_result_failed_providers_property():
    result = MultiProviderIntegrationValidationResult(
        expected_provider_count=2,
        validated_provider_count=2,
        successful_provider_count=1,
        failed_provider_count=1,
        total_model_count=2,
        provider_results=(
            ProviderValidationResult(
                provider_name="openai",
                registered=True,
                instantiated=True,
                model_count=2,
                models=("model-a", "model-b"),
                successful=True,
            ),
            ProviderValidationResult(
                provider_name="ollama",
                registered=False,
                instantiated=False,
                model_count=0,
                models=(),
                successful=False,
                errors=("Provider is not registered.",),
            ),
        ),
    )

    assert result.failed_providers == ("ollama",)
    assert result.successful_providers == ("openai",)
    assert result.is_successful is False
