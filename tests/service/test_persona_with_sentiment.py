import pytest
from unittest.mock import AsyncMock
from src.service.persona_with_sentiment import get_persona_with_sentiment
from src.schemas.persona_model import (
    Persona,
    ExpertiseLevel,
    Personality,
    PersonalityFocus,
    CommunicationRules,
)


@pytest.mark.anyio
def build_persona():
    return Persona(
        name="Owen",
        role="Owner, Golden Bikes",
        location="Test Location",
        background=["bg"],
        goals=["goal"],
        expertise_level=ExpertiseLevel(business="high", technology="low"),
        personality=Personality(
            tone=["friendly"],
            professionalism="casual",
            focus=PersonalityFocus(can_tangent=False, refocus_easily=True),
        ),
        communication_rules=CommunicationRules(avoid=["jargon"]),
    )


@pytest.mark.anyio
async def test_persona_with_valid_sentiment():
    persona = build_persona()
    mock_sentiment_service = AsyncMock()
    mock_sentiment_service.get_sentiment.return_value = type(
        "Sentiment", (), {"sentiment": 5.5}
    )()
    updated = await get_persona_with_sentiment(
        persona, mock_sentiment_service, "conv-id"
    )
    assert updated.personality.sentiment == 5.5


@pytest.mark.anyio
async def test_persona_with_no_sentiment():
    persona = build_persona()
    mock_sentiment_service = AsyncMock()
    mock_sentiment_service.get_sentiment.return_value = None
    updated = await get_persona_with_sentiment(
        persona, mock_sentiment_service, "conv-id"
    )
    assert updated.personality.sentiment is None


@pytest.mark.anyio
async def test_persona_with_negative_sentiment():
    persona = build_persona()
    mock_sentiment_service = AsyncMock()
    mock_sentiment_service.get_sentiment.return_value = type(
        "Sentiment", (), {"sentiment": -10.0}
    )()
    updated = await get_persona_with_sentiment(
        persona, mock_sentiment_service, "conv-id"
    )
    assert updated.personality.sentiment == -10.0


@pytest.mark.anyio
async def test_persona_with_positive_sentiment():
    persona = build_persona()
    mock_sentiment_service = AsyncMock()
    mock_sentiment_service.get_sentiment.return_value = type(
        "Sentiment", (), {"sentiment": 10.0}
    )()
    updated = await get_persona_with_sentiment(
        persona, mock_sentiment_service, "conv-id"
    )
    assert updated.personality.sentiment == 10.0


@pytest.mark.anyio
async def test_persona_immutability():
    persona = build_persona()
    mock_sentiment_service = AsyncMock()
    mock_sentiment_service.get_sentiment.return_value = type(
        "Sentiment", (), {"sentiment": 2.0}
    )()
    updated = await get_persona_with_sentiment(
        persona, mock_sentiment_service, "conv-id"
    )
    assert updated is not persona
    assert persona.personality.sentiment is None
    assert updated.personality.sentiment == 2.0


@pytest.mark.anyio
async def test_persona_with_invalid_sentiment_type():
    persona = build_persona()
    mock_sentiment_service = AsyncMock()
    # Simulate DB returning a string instead of a number
    mock_sentiment_service.get_sentiment.return_value = type(
        "Sentiment", (), {"sentiment": "not_a_number"}
    )()
    try:
        updated = await get_persona_with_sentiment(
            persona, mock_sentiment_service, "conv-id"
        )
        # If no exception, should fall back to None or ignore invalid value
        assert updated.personality.sentiment is None or isinstance(
            updated.personality.sentiment, float
        )
    except (TypeError, ValueError):
        assert True
