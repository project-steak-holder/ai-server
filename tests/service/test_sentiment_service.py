"""
Unit tests for SentimentService.
"""

import pytest
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

from src.service.sentiment_service import SentimentService
from src.models.sentiment import Sentiment


@pytest.fixture
def mock_sentiment_repository():
    mock = MagicMock()
    mock.get_sentiment = AsyncMock(return_value=None)
    mock.update_sentiment = AsyncMock(return_value=None)
    return mock


@pytest.fixture
def sentiment_data_service(mock_sentiment_repository):
    return SentimentService(sentiment_repository=mock_sentiment_repository)


@pytest.mark.anyio
async def test_get_sentiment(sentiment_data_service, mock_sentiment_repository):
    conversation_id = "conv-123"
    sentiment_obj = MagicMock(spec=Sentiment)
    mock_sentiment_repository.get_sentiment.return_value = sentiment_obj
    result = await sentiment_data_service.get_sentiment(conversation_id)
    mock_sentiment_repository.get_sentiment.assert_awaited_once_with(conversation_id)
    assert result is sentiment_obj


@pytest.mark.anyio
async def test_update_sentiment(sentiment_data_service, mock_sentiment_repository):
    conversation_id = "conv-456"
    new_value = Decimal("3.14")
    sentiment_obj = MagicMock(spec=Sentiment)
    mock_sentiment_repository.update_sentiment.return_value = sentiment_obj
    result = await sentiment_data_service.update_sentiment(conversation_id, new_value)
    mock_sentiment_repository.update_sentiment.assert_awaited_once_with(
        conversation_id, new_value
    )
    assert result is sentiment_obj


@pytest.mark.anyio
async def test_update_sentiment_not_found(
    sentiment_data_service, mock_sentiment_repository
):
    conversation_id = "conv-789"
    new_value = Decimal("-2.71")
    mock_sentiment_repository.update_sentiment.return_value = None
    result = await sentiment_data_service.update_sentiment(conversation_id, new_value)
    mock_sentiment_repository.update_sentiment.assert_awaited_once_with(
        conversation_id, new_value
    )
    assert result is None
