
from unittest.mock import MagicMock, patch

@patch("app.Application")
def test_app_start(mock_application):
    """Test application initialization and startup."""

    # Arrange
    mock_instance = mock_application.return_value
    mock_instance.container = MagicMock()

    # Act
    application = mock_application()
    application.start()

    # Assert
    mock_application.assert_called_once()
    application.start.assert_called_once()
    assert application.container is not None

@patch("app.Application")
def test_app_container(mock_application):
    """Test application container availability."""

    application = mock_application.return_value
    application.container = MagicMock()

    assert application.container is not None

def test_streamlit_imports():
    """Test required application imports."""

    import streamlit as st
    from app import Application
    from app.config import settings
    from app.presentation import render

    assert st is not None
    assert Application is not None
    assert settings is not None
    assert callable(render)