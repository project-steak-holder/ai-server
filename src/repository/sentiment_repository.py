from sqlalchemy import select
from src.repository.base import BaseCRUDRepository
from src.models.sentiment import Sentiment
from decimal import Decimal

__all__ = ["SentimentRepository"]


class SentimentRepository(BaseCRUDRepository[Sentiment]):
    """Repository for managing database operations related to sentiment."""

    async def get_sentiment(self, conversation_id: str) -> Sentiment | None:
        """Fetch the sentiment record for a given conversation."""
        stmt = select(Sentiment).where(Sentiment.conversation_id == conversation_id)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def update_sentiment(
        self, conversation_id: str, new_value: float | Decimal
    ) -> Sentiment | None:
        """Update the sentiment value for a given conversation."""
        sentiment = await self.get_sentiment(conversation_id)
        if sentiment:
            # Use setattr to avoid mypy/SQLAlchemy type confusion
            setattr(
                sentiment,
                "sentiment",
                new_value
                if isinstance(new_value, Decimal)
                else Decimal(str(new_value)),
            )
            await self.session.commit()
            await self.session.refresh(sentiment)
        return sentiment
