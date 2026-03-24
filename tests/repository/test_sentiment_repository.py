"""Unit tests for SentimentRepository."""

from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from decimal import Decimal

from src.repository.sentiment_repository import SentimentRepository
from src.models.sentiment import Sentiment


class RepoResultScalarsFirst:
    def __init__(self, value):
        self._value = value

    def scalars(self):
        return self

    def first(self):
        return self._value


# Test get_sentiment
@pytest.mark.anyio
async def test_get_sentiment():
    session = AsyncMock()
    repo = SentimentRepository(session)
    sentiment_obj = MagicMock(spec=Sentiment)
    session.execute.return_value = RepoResultScalarsFirst(sentiment_obj)
    result = await repo.get_sentiment("c1")
    assert result is sentiment_obj
    session.execute.assert_awaited()


# Test update_sentiment (existing sentiment)
@pytest.mark.anyio
async def test_update_sentiment_existing():
    session = AsyncMock()
    repo = SentimentRepository(session)
    sentiment_obj = MagicMock(spec=Sentiment)
    with patch.object(
        repo, "get_sentiment", AsyncMock(return_value=sentiment_obj)
    ) as mock_get:
        session.commit = AsyncMock()
        session.refresh = AsyncMock()
        updated = await repo.update_sentiment("c1", Decimal("2.34"))
        assert updated is sentiment_obj
        mock_get.assert_awaited_once_with("c1")
        session.commit.assert_awaited_once()
        session.refresh.assert_awaited_once_with(sentiment_obj)
        assert getattr(sentiment_obj, "sentiment") == Decimal("2.34")


# Test update_sentiment (no sentiment found)
@pytest.mark.anyio
async def test_update_sentiment_not_found():
    session = AsyncMock()
    repo = SentimentRepository(session)
    with patch.object(repo, "get_sentiment", AsyncMock(return_value=None)) as mock_get:
        updated = await repo.update_sentiment("c2", Decimal("1.23"))
        assert updated is None
        mock_get.assert_awaited_once_with("c2")
