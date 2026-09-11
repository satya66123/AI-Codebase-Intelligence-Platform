from app.application.container import ApplicationContainer
from app.config import validate_provider_configuration
from app.core import configure_logging, get_logger


class Application:
    def __init__(self) -> None:
        configure_logging()
        self._logger = get_logger(__name__)

        validate_provider_configuration()

        self._container = ApplicationContainer()

        self._logger.info(
            "Application initialized successfully."
        )

    @property
    def container(self) -> ApplicationContainer:
        return self._container

    def start(self) -> None:
        self._logger.info(
            "AI Codebase Intelligence Platform started."
        )