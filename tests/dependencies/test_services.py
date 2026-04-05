"""Unit tests for service dependency factories."""

from unittest.mock import MagicMock

from src.dependencies.services import (
    get_agent_service,
    get_model_service,
)
from src.dependencies.database import get_sentiment_service as get_db_sentiment_service
from src.service.sentiment_service import SentimentService


def test_dependencies_service_factories():

    model_service = get_model_service()
    assert model_service.__class__.__name__ == "ModelService"

    mock_model_service = MagicMock(name="ModelService")
    mock_message_service = MagicMock(name="MessageService")
    mock_sentiment_service = MagicMock(name="SentimentService")
    agent_service = get_agent_service(
        mock_model_service, mock_message_service, mock_sentiment_service
    )

    assert agent_service.message_service == mock_message_service
    assert agent_service.model_service == mock_model_service

    # Test get_sentiment_service returns SentimentService instance with a mock repo
    mock_repo = MagicMock()
    sentiment_service = get_db_sentiment_service(mock_repo)
    assert isinstance(sentiment_service, SentimentService)
    assert sentiment_service.sentiment_repository is mock_repo
