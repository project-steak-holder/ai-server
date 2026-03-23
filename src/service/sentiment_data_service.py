"""
Sentiment persistence service
Project SteakHolder
"""

from src.repository.sentiment_repository import SentimentRepository
from src.models.sentiment import Sentiment
from decimal import Decimal


class SentimentDataService:
    """Service for handling sentiment data."""

    def __init__(self, sentiment_repository: SentimentRepository) -> None:
        self.sentiment_repository = sentiment_repository

    async def get_sentiment(self, conversation_id: str) -> Sentiment | None:
        """Retrieve the sentiment record for a given conversation."""
        return await self.sentiment_repository.get_sentiment(conversation_id)

    async def update_sentiment(
        self, conversation_id: str, new_value: float | Decimal
    ) -> Sentiment | None:
        """Update the sentiment value for a given conversation."""
        return await self.sentiment_repository.update_sentiment(
            conversation_id, new_value
        )
