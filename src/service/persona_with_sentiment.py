from copy import deepcopy

from src.middlewares.events import wide_event
from src.schemas.persona_model import Persona


@wide_event("get_persona_with_sentiment")
async def get_persona_with_sentiment(
    persona: Persona, sentiment_service, conversation_id: str
) -> Persona:
    """
    Returns deep copy of persona model with the current sentiment injected.
    should be called BEFORE any process/run query methods.
    """
    persona_copy = deepcopy(persona)
    sentiment_obj = await sentiment_service.get_sentiment(conversation_id)
    if sentiment_obj is not None:
        persona_copy.personality.sentiment = float(sentiment_obj.sentiment)
    else:
        persona_copy.personality.sentiment = None
    return persona_copy
