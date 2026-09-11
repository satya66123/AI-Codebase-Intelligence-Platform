from app.config.models import PROVIDER_MODELS


EXPECTED_PROVIDER_COUNT = 8
EXPECTED_MODEL_COUNT = 30


def validate_provider_configuration() -> None:
    if len(PROVIDER_MODELS) != EXPECTED_PROVIDER_COUNT:
        raise ValueError(
            f"Expected {EXPECTED_PROVIDER_COUNT} providers, "
            f"found {len(PROVIDER_MODELS)}."
        )

    model_count = sum(
        len(models)
        for models in PROVIDER_MODELS.values()
    )

    if model_count != EXPECTED_MODEL_COUNT:
        raise ValueError(
            f"Expected {EXPECTED_MODEL_COUNT} models, "
            f"found {model_count}."
        )

    for provider, models in PROVIDER_MODELS.items():
        if not provider:
            raise ValueError("Provider name cannot be empty.")

        if not models:
            raise ValueError(
                f"Provider '{provider}' must have at least one model."
            )