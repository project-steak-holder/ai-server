"""
Unit tests for SentimentService.
"""

import pytest

from unittest.mock import AsyncMock, MagicMock
from src.models.sentiment import Sentiment


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
    new_value = "3.14"
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
    new_value = "-2.71"
    mock_sentiment_repository.update_sentiment.return_value = None
    result = await sentiment_data_service.update_sentiment(conversation_id, new_value)
    mock_sentiment_repository.update_sentiment.assert_awaited_once_with(
        conversation_id, new_value
    )
    assert result is None


@pytest.mark.anyio
async def test_get_current_sentiment_for_persona_valid(
    sentiment_data_service, build_persona
):
    persona = build_persona
    sentiment_data_service.model_service.get_model.return_value = persona
    sentiment_data_service.get_sentiment = AsyncMock(
        return_value=type("Sentiment", (), {"sentiment": 5.5})()
    )
    updated = await sentiment_data_service.get_persona_w_current_sentiment("conv-id")
    assert updated.personality.sentiment == 5.5


@pytest.mark.anyio
async def test_get_current_sentiment_for_persona_none(
    sentiment_data_service, build_persona
):
    persona = build_persona
    sentiment_data_service.model_service.get_model.return_value = persona
    sentiment_data_service.get_sentiment = AsyncMock(return_value=None)
    updated = await sentiment_data_service.get_persona_w_current_sentiment("conv-id")
    assert updated.personality.sentiment == 0.00


@pytest.mark.anyio
async def test_get_current_sentiment_for_persona_negative(
    sentiment_data_service, build_persona
):
    persona = build_persona
    sentiment_data_service.model_service.get_model.return_value = persona
    sentiment_data_service.get_sentiment = AsyncMock(
        return_value=type("Sentiment", (), {"sentiment": -10.0})()
    )
    updated = await sentiment_data_service.get_persona_w_current_sentiment("conv-id")
    assert updated.personality.sentiment == -10.0


@pytest.mark.anyio
async def test_get_current_sentiment_for_persona_positive(
    sentiment_data_service, build_persona
):
    persona = build_persona
    sentiment_data_service.model_service.get_model.return_value = persona
    sentiment_data_service.get_sentiment = AsyncMock(
        return_value=type("Sentiment", (), {"sentiment": 10.0})()
    )
    updated = await sentiment_data_service.get_persona_w_current_sentiment("conv-id")
    assert updated.personality.sentiment == 10.0


@pytest.mark.anyio
async def test_get_current_sentiment_for_persona_immutability(
    sentiment_data_service, build_persona
):
    persona = build_persona
    sentiment_data_service.model_service.get_model.return_value = persona
    sentiment_data_service.get_sentiment = AsyncMock(
        return_value=type("Sentiment", (), {"sentiment": 2.0})()
    )
    updated = await sentiment_data_service.get_persona_w_current_sentiment("conv-id")
    assert updated is not persona
    assert persona.personality.sentiment == 0.00
    assert updated.personality.sentiment == 2.0


@pytest.mark.anyio
async def test_get_current_sentiment_value_found(sentiment_data_service):
    sentiment_obj = MagicMock(spec=Sentiment)
    sentiment_obj.sentiment = 3.21
    sentiment_data_service.get_sentiment = AsyncMock(return_value=sentiment_obj)
    result = await sentiment_data_service.get_current_sentiment_value("conv-1")
    assert result == 3.21


@pytest.mark.anyio
async def test_get_current_sentiment_value_not_found(sentiment_data_service):
    sentiment_data_service.get_sentiment = AsyncMock(return_value=None)
    result = await sentiment_data_service.get_current_sentiment_value("conv-3")
    assert result == 0.00
