"""Unit tests for service dependency factories."""

from unittest.mock import MagicMock, patch

from src.dependencies.services import (
    get_agent_service,
    get_model_service,
    get_sentiment_data_service,
)
from src.dependencies.database import get_sentiment_service
from src.service.sentiment_data_service import SentimentDataService


def test_dependencies_service_factories():

    model_service = get_model_service()
    assert model_service.__class__.__name__ == "ModelService"

    with (
        patch("src.dependencies.services.get_model_service", return_value="model"),
        patch("src.dependencies.services.get_message_service", return_value="message"),
    ):
        agent_service = get_agent_service("model", "message")

    assert agent_service.message_service == "message"
    assert agent_service.model_service == "model"

    # Test get_sentiment_service returns SentimentDataService instance with a mock repo
    mock_repo = MagicMock()
    sentiment_service = get_sentiment_service(mock_repo)
    assert isinstance(sentiment_service, SentimentDataService)
    assert sentiment_service.sentiment_repository is mock_repo

    # Optionally, check get_sentiment_data_service is a "Depends" object
    assert type(get_sentiment_data_service).__name__ == "Depends"
    assert get_sentiment_data_service.dependency == get_sentiment_service
