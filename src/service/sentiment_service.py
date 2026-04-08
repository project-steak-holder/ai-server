"""
Sentiment persistence service
Project SteakHolder
"""

from src.middlewares.events import add_event_context, wide_event
from src.repository.sentiment_repository import SentimentRepository
from src.models.sentiment import Sentiment
from src.schemas.persona_model import Persona
from decimal import Decimal
from typing import Optional, Union
from copy import deepcopy


class SentimentService:
    def __init__(self, sentiment_repository: SentimentRepository) -> None:
        self.sentiment_repository = sentiment_repository

    @wide_event("get_sentiment")
    async def get_sentiment(self, conversation_id: str) -> Optional[Sentiment]:
        """Retrieve accrued sentiment value for given conversation."""
        sentiment = await self.sentiment_repository.get_sentiment(conversation_id)
        add_event_context(
            current_sentiment_value=float(sentiment.sentiment) if sentiment else None,
        )
        return sentiment

    @wide_event("update_sentiment")
    async def update_sentiment(
        self, conversation_id: str, new_value: "Union[float, Decimal]"
    ) -> Optional[Sentiment]:
        """Persist updated sentiment value for given conversation."""
        sentiment = await self.sentiment_repository.update_sentiment(
            conversation_id, new_value
        )
        add_event_context(
            new_sentiment_value=float(new_value),
        )
        return sentiment

    @wide_event("get_persona")
    async def get_persona_w_current_sentiment(
        self, persona: Persona, conversation_id: str
    ) -> Persona:
        """
        Returns deep copy of persona model with the current sentiment injected.
        Should be called BEFORE any process/run query methods.
        """
        persona_copy = deepcopy(persona)
        sentiment_obj = await self.get_sentiment(conversation_id)
        if sentiment_obj is not None:
            persona_copy.personality.sentiment = float(sentiment_obj.sentiment)
        else:
            persona_copy.personality.sentiment = None
        return persona_copy

    async def get_current_sentiment_value(self, conversation_id: str) -> Decimal:
        """
        Retrieve current sentiment value for a conversation as a Decimal.
        Returns Decimal("0.00") if not found or not set.
        """
        sentiment_obj = await self.get_sentiment(conversation_id)
        if sentiment_obj and sentiment_obj.sentiment is not None:
            return Decimal(str(sentiment_obj.sentiment))
        return Decimal("0.00")
