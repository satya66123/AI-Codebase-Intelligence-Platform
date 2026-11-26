
from unittest.mock import MagicMock

import pytest

from appy.application.repository_agent import RepositoryAnalysisResult
from appy.application.repository_discovery_integration_service import (
    RepositoryDiscoveryIntegrationError,
    RepositoryDiscoveryIntegrationService,
)


def test_restore_result_restores_repository_state():
    service = RepositoryDiscoveryIntegrationService()

    result = MagicMock(spec=RepositoryAnalysisResult)

    service.restore_result(result)

    assert service._last_result is result


def test_restore_result_rejects_none():
    service = RepositoryDiscoveryIntegrationService()

    with pytest.raises(RepositoryDiscoveryIntegrationError):
        service.restore_result(None)


def test_search_files_works_after_restoring_result():
    index_service = MagicMock()
    index_service.search_files.return_value = [
        {"path": "main.py"}
    ]

    service = RepositoryDiscoveryIntegrationService(
        index_service=index_service,
    )

    result = MagicMock(spec=RepositoryAnalysisResult)
    result.index = {"files": []}

    service.restore_result(result)

    search_results = service.search_files("main")

    assert search_results == [{"path": "main.py"}]

    index_service.search_files.assert_called_once_with(
        result.index,
        "main",
    )
