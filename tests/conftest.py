"""
Test fixtures for pytest.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
import uuid
from datetime import datetime, timezone

from src.service.agent_service import AgentService
from src.service.message_service import MessageService
from src.service.model_service import ModelService
from src.repository.message_repository import MessageRepository
from src.models.message import Message as MessageModel
from src.schemas.message_model import MessageType


@pytest.fixture
def sample_persona():
    """Create a canonical sample persona for testing."""
    from src.schemas.persona_model import (
        Persona,
        ExpertiseLevel,
        Personality,
        PersonalityFocus,
        CommunicationRules,
    )

    return Persona(
        name="Owen",
        role="Owner, Golden Bikes",
        location="Golden, CO",
        background=["Entrepreneur", "Cycling enthusiast"],
        goals=["Build successful bike rental business"],
        expertise_level=ExpertiseLevel(business="high", technology="medium"),
        personality=Personality(
            tone=["friendly", "professional"],
            professionalism="business casual",
            focus=PersonalityFocus(can_tangent=False, refocus_easily=True),
        ),
        communication_rules=CommunicationRules(avoid=["technical jargon"]),
    )


@pytest.fixture
def sample_project():
    """Create a canonical sample project for testing."""
    from src.schemas.project_model import Project

    return Project(
        project_name="Golden Bikes Rental System",
        business_summary="A bike rental platform for urban commuters",
        requirements=[],
    )


@pytest.fixture
def mock_message_service():
    """Create a mock MessageService."""
    mock = MagicMock(spec=MessageService)

    # Create mock message objects
    def create_mock_message(content, msg_type):
        msg = MagicMock(spec=MessageModel)
        msg.id = uuid.uuid4()
        msg.conversation_id = uuid.uuid4()
        msg.user_id = uuid.uuid4()
        msg.content = content
        msg.type = msg_type
        msg.created_at = datetime.now(timezone.utc)
        msg.updated_at = datetime.now(timezone.utc)
        return msg

    # Mock async methods
    mock.save_user_message = AsyncMock(
        return_value=create_mock_message("test message", MessageType.USER)
    )
    mock.save_ai_message = AsyncMock(
        return_value=create_mock_message("test response", MessageType.AI)
    )
    mock.get_conversation_history = AsyncMock(return_value=[])

    return mock


@pytest.fixture
def mock_message_repository():
    """Create a mock MessageRepository."""
    mock = MagicMock(spec=MessageRepository)

    def create_mock_message(conversation_id, user_id, content, msg_type):
        msg = MagicMock(spec=MessageModel)
        msg.id = uuid.uuid4()
        msg.conversation_id = (
            uuid.UUID(conversation_id)
            if isinstance(conversation_id, str)
            else conversation_id
        )
        msg.user_id = uuid.UUID(user_id) if isinstance(user_id, str) else user_id
        msg.content = content
        msg.type = msg_type
        msg.created_at = datetime.now(timezone.utc)
        msg.updated_at = datetime.now(timezone.utc)
        return msg

    # Mock async methods
    mock.save_message = AsyncMock(
        side_effect=lambda *args, **kwargs: create_mock_message(
            kwargs.get("conversation_id", args[0] if len(args) > 0 else None),
            kwargs.get("user_id", args[1] if len(args) > 1 else None),
            kwargs.get("content", args[2] if len(args) > 2 else None),
            kwargs.get("type", args[3] if len(args) > 3 else None),
        )
    )
    mock.get_messages_by_conversation_id = AsyncMock(return_value=[])

    return mock


@pytest.fixture
def message_service(mock_message_repository):
    """Create a MessageService with mocked repository."""
    return MessageService(message_repository=mock_message_repository)


@pytest.fixture
def agent_service(mock_message_service):
    """Create an AgentService with mocked dependencies."""
    mock_model_service = MagicMock(spec=ModelService)
    # Provide real Persona and Project for _load_model
    from src.schemas.persona_model import (
        Persona,
        ExpertiseLevel,
        Personality,
        PersonalityFocus,
        CommunicationRules,
    )
    from src.schemas.project_model import Project
    from src.schemas.sentiment_scale_model import SentimentScale, SentimentScaleEntry
    from src.schemas.listening_cues_model import ListeningCues, ListeningCue
    from src.schemas.instructions_model import InstructionsModel

    persona = Persona(
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
    project = Project(
        project_name="Golden Bikes Rental System",
        business_summary="summary",
        requirements=[],
    )
    sentiment_scale = SentimentScale(
        purpose="translate between numerical sentiment score and persona-guiding sentiment verb",
        scale=[
            SentimentScaleEntry(score=-10, label="Furious"),
            SentimentScaleEntry(score=-8, label="Angry"),
            SentimentScaleEntry(score=-6, label="Frustrated"),
            SentimentScaleEntry(score=-4, label="Annoyed"),
            SentimentScaleEntry(score=-2, label="Disinterested"),
            SentimentScaleEntry(score=0, label="Neutral"),
            SentimentScaleEntry(score=2, label="Receptive"),
            SentimentScaleEntry(score=4, label="Engaged"),
            SentimentScaleEntry(score=6, label="Enthusiastic"),
            SentimentScaleEntry(score=8, label="Excited"),
            SentimentScaleEntry(score=10, label="Elated"),
        ],
    )
    listening_cues = ListeningCues(
        purpose="backend LLM listens for these in stakeholder input",
        outcome="Guide agent response tone and feedback.",  # Add required field
        cues={
            "positive": [
                ListeningCue(cue="values stakeholder time", score=0.5),
                ListeningCue(cue="asks permission", score=0.5),
                ListeningCue(cue="acknowledges stakeholder input", score=1),
                ListeningCue(cue="shows stakeholder benefit", score=1),
                ListeningCue(cue="effective listening (80/20)", score=0.5),
                ListeningCue(cue="asks open-ended questions", score=1),
                ListeningCue(cue="asks relevant follow-up", score=1),
                ListeningCue(cue="asks about stakeholder goals", score=2),
                ListeningCue(cue="accurately paraphrases input", score=2),
                ListeningCue(cue="asks for specific example", score=1.5),
                ListeningCue(cue="confirms understanding", score=1),
            ],
            "negative": [
                ListeningCue(cue="lack of preparation", score=-1.5),
                ListeningCue(cue="inconsistent with stakeholder input", score=-1.5),
                ListeningCue(cue="disrespectful", score=-3),
                ListeningCue(cue="offers premature solution", score=-2.5),
                ListeningCue(cue="no follow-up on vague input", score=-2),
                ListeningCue(cue="ignores requirement/constraint", score=-3),
                ListeningCue(
                    cue=">2 questions", score=-1.5, note="-0.05 each extra, cap -3.0"
                ),
            ],
        },
    )
    instructions = InstructionsModel(
        purpose="Primary instructions and rules for dynamic agent sentiment; references other models for cues and scale.",
        precedence=True,
        references=["listening_cues", "sentiment_scale"],
        instructions=[
            "1. Receive the following inputs: user message, current_sentiment (from persona), listening_cues, and sentiment_scale.",
            "2. Analyze the user message for evidence of listening cues, using the definitions in listening_cues.",
            "3. For each detected cue, add its score to a running total (sentiment_delta). Select up to 3 positive and 2 negative cues per turn, with no overlap; prefer the most specific/high impact cues.",
            "4. Require explicit evidence for each cue; do not infer cues without clear support in the user message.",
            "5. If both positive and negative cues are present, include both and sum their scores. For multi-question cues, treat as a single cue and apply the cap as defined.",
            "6. Calculate sentiment_delta as the sum of the selected cue scores, rounded to two decimal places. If no cues are detected, sentiment_delta = 0.00.",
            "7. Calculate updated_sentiment = current_sentiment + sentiment_delta. Clamp updated_sentiment to the range -10 to +10.",
            "8. Use sentiment_scale to map updated_sentiment to the nearest sentiment label. Use this label to guide the tone of the response.",
            "9. Update the persona's sentiment field with the updated_sentiment value before generating the response.",
            "10. Use the updated persona (including the new sentiment) as the basis for generating the response, ensuring the tone matches the sentiment label.",
            "11. Generate a response message using the updated sentiment label for tone.",
            "12. Return only the following structured output: { 'message': <response>, 'sentiment_delta': <decimal> }.",
            "13. Do not include any internal reasoning, <think> tags, or cues in the output; only return the structured response.",
            "14. If the output cannot be generated as specified, set sentiment_delta = 0.00 and return an appropriate message.",
        ],
    )
    # Do not mock protected member _load_model; only mock public interface
    mock_model_service.get_model.side_effect = lambda name, expected_type=None: (
        persona
        if name == "persona"
        else project
        if name == "project"
        else sentiment_scale
        if name == "sentiment_scale"
        else listening_cues
        if name == "listening_cues"
        else instructions
        if name == "instructions"
        else None
    )
    from unittest.mock import AsyncMock

    mock_sentiment_service = MagicMock()
    mock_sentiment_service.get_sentiment = AsyncMock(return_value=None)
    mock_sentiment_service.update_sentiment = AsyncMock(return_value=None)
    # Ensure get_persona_w_current_sentiment is always an AsyncMock
    mock_sentiment_service.get_persona_w_current_sentiment = AsyncMock(
        return_value=None
    )
    return AgentService(
        model_service=mock_model_service,
        message_service=mock_message_service,
        sentiment_service=mock_sentiment_service,
    )


@pytest.fixture
def mock_sentiment_repository():
    """Create a mock SentimentRepository."""
    mock = MagicMock()
    mock.get_sentiment = AsyncMock(return_value=None)
    mock.update_sentiment = AsyncMock(return_value=None)
    return mock


@pytest.fixture
def sentiment_data_service(mock_sentiment_repository):
    """Create a SentimentService with mocked repository."""
    from src.service.sentiment_service import SentimentService

    return SentimentService(
        sentiment_repository=mock_sentiment_repository, model_service=MagicMock()
    )


@pytest.fixture
def build_persona():
    """Build a Persona instance for sentiment tests."""
    from src.schemas.persona_model import (
        Persona,
        ExpertiseLevel,
        Personality,
        PersonalityFocus,
        CommunicationRules,
    )

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
            sentiment=0.00,
        ),
        communication_rules=CommunicationRules(avoid=["jargon"]),
    )


@pytest.fixture
async def persona_with_sentiment(agent_service):
    """Persona with current sentiment for agent service tests."""
    persona = agent_service.load_persona()
    # Use a dummy conversation_id for tests
    return await agent_service.sentiment_service.get_persona_w_current_sentiment(
        persona, "test-conv-id"
    )
