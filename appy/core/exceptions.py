class DigitalTwinError(Exception):
    """Base exception for the Codebase Intelligence platform."""


class ConfigurationError(DigitalTwinError):
    """Raised when application configuration is invalid."""


class ProviderError(DigitalTwinError):
    """Raised when an AI provider operation fails."""


class ModelError(DigitalTwinError):
    """Raised when an AI model operation fails."""