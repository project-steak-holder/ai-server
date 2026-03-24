"""Unit tests for service dependency factories."""

from unittest.mock import MagicMock, patch

from src.dependencies.services import (
    get_agent_service,
    get_persona_service,
    get_project_service,
    get_sentiment_data_service,
)
from src.dependencies.database import get_sentiment_service
from src.service.sentiment_data_service import SentimentDataService


def test_dependencies_service_factories():
    persona_service = get_persona_service()
    project_service = get_project_service()

    assert persona_service.__class__.__name__ == "PersonaService"
    assert project_service.__class__.__name__ == "ProjectService"

    message_service = MagicMock()
    with (
        patch("src.dependencies.services.get_persona_service", return_value="persona"),
        patch("src.dependencies.services.get_project_service", return_value="project"),
    ):
        agent_service = get_agent_service(message_service)

    assert agent_service.message_service is message_service
    assert agent_service.persona_service == "persona"
    assert agent_service.project_service == "project"

    # Test get_sentiment_service returns SentimentDataService instance with a mock repo
    mock_repo = MagicMock()
    sentiment_service = get_sentiment_service(mock_repo)
    assert isinstance(sentiment_service, SentimentDataService)
    assert sentiment_service.sentiment_repository is mock_repo

    # Optionally, check get_sentiment_data_service is a "Depends" object
    assert type(get_sentiment_data_service).__name__ == "Depends"
    assert get_sentiment_data_service.dependency == get_sentiment_service
