"""
Sentiment persistence service
Project SteakHolder
"""

from src.middlewares.events import add_event_context, wide_event
from src.repository.sentiment_repository import SentimentRepository
from src.models.sentiment import Sentiment
from src.schemas.persona_model import Persona
from typing import Optional

from src.service.model_service import ModelService


class SentimentService:
    def __init__(
        self, sentiment_repository: SentimentRepository, model_service: ModelService
    ) -> None:
        self.sentiment_repository = sentiment_repository
        self.model_service: ModelService = model_service

    @wide_event("get_sentiment")
    async def get_sentiment(self, conversation_id: str) -> Optional[Sentiment]:
        """Retrieve accrued sentiment value for given conversation."""
        conversation_sentiment = await self.sentiment_repository.get_sentiment(
            conversation_id
        )
        add_event_context(
            current_sentiment_value=conversation_sentiment.sentiment
            if conversation_sentiment
            else None,
        )
        return conversation_sentiment

    @wide_event("update_sentiment")
    async def update_sentiment(
        self,
        conversation_id: str,
        new_value: float,
    ) -> Optional[Sentiment]:
        """Persist updated sentiment value for given conversation."""
        updated_sentiment = await self.sentiment_repository.update_sentiment(
            conversation_id, new_value
        )
        add_event_context(
            new_sentiment_value=float(new_value),
        )
        return updated_sentiment

    @wide_event("get_persona")
    async def get_persona_w_current_sentiment(self, conversation_id: str) -> Persona:
        """
        Returns deep copy of persona model with the current sentiment injected.
        Should be called BEFORE any process/run query methods.
        """
        persona = self.model_service.get_model("persona", Persona)
        sentiment_value = await self.get_current_sentiment_value(conversation_id)
        return persona.model_copy(
            deep=True,
            update={
                "personality": persona.personality.model_copy(
                    update={"sentiment": sentiment_value}
                )
            },
        )

    async def get_current_sentiment_value(self, conversation_id: str) -> float:
        """
        Retrieve current sentiment value for a conversation.
        Returns 0.00 if not found or not set.
        """
        sentiment_obj = await self.get_sentiment(conversation_id)
        if sentiment_obj is None:
            return 0.00

        return sentiment_obj.sentiment
