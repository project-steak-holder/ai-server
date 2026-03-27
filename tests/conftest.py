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
    mock_model_service._load_model.side_effect = lambda name: (
        persona if name == "persona" else project if name == "project" else None
    )
    mock_model_service.get_model.side_effect = lambda name: (
        persona if name == "persona" else project if name == "project" else None
    )
    return AgentService(
        model_service=mock_model_service,
        message_service=mock_message_service,
    )
