from sqlalchemy import select
from src.repository.base import BaseCRUDRepository
from src.models.sentiment import Sentiment

__all__ = ["SentimentRepository"]


class SentimentRepository(BaseCRUDRepository[Sentiment]):
    """Repository for managing database operations related to sentiment."""

    async def get_sentiment(self, conversation_id: str) -> Sentiment | None:
        """Fetch the sentiment record for a given conversation."""
        stmt = select(Sentiment).where(Sentiment.conversation_id == conversation_id)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def update_sentiment(
        self, conversation_id: str, new_value: float
    ) -> Sentiment:
        """Upsert the sentiment value for a given conversation."""
        sentiment = await self.get_sentiment(conversation_id)
        if sentiment:
            sentiment.sentiment = new_value
        else:
            sentiment = Sentiment(conversation_id=conversation_id, sentiment=new_value)
        return await self.update(sentiment)
