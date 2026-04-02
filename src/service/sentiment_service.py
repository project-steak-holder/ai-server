"""
Sentiment persistence service
Project SteakHolder
"""

from src.middlewares.events import add_event_context, wide_event
from src.repository.sentiment_repository import SentimentRepository
from src.models.sentiment import Sentiment
from decimal import Decimal


class SentimentDataService:
    """Service for handling sentiment data."""

    def __init__(self, sentiment_repository: SentimentRepository) -> None:
        self.sentiment_repository = sentiment_repository

    @wide_event("get_sentiment")
    async def get_sentiment(self, conversation_id: str) -> Sentiment | None:
        """Retrieve the sentiment record for a given conversation."""
        sentiment = await self.sentiment_repository.get_sentiment(conversation_id)
        add_event_context(
            current_sentiment_value=float(sentiment.sentiment) if sentiment else None,
        )
        return sentiment

    @wide_event("update_sentiment")
    async def update_sentiment(
        self, conversation_id: str, new_value: float | Decimal
    ) -> Sentiment | None:
        """Update the sentiment value for a given conversation."""
        sentiment = await self.sentiment_repository.update_sentiment(
            conversation_id, new_value
        )
        add_event_context(
            new_sentiment_value=float(new_value),
        )
        return sentiment
