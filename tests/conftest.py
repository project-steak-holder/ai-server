"""
Test fixtures for pytest.
"""

from unittest.mock import AsyncMock, MagicMock
import pytest
import uuid

from src.service.agent_service import AgentService
from src.service.persona_service import PersonaService
from src.service.project_service import ProjectService
from src.service.message_service import MessageService
from src.repository.model_repository import MessageRepository
from src.schemas.persona_model import (
    CommunicationRules,
    ExpertiseLevel,
    Persona,
    Personality,
    PersonalityFocus,
)
from src.schemas.project_model import Project
from src.models.message import Message as MessageModel, MessageType
from datetime import datetime, timezone


@pytest.fixture
def mock_persona_service():
    """Create a mock PersonaService."""
    mock = MagicMock(spec=PersonaService)
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
    mock.load_persona.return_value = persona
    mock.get_persona.return_value = persona
    return mock


@pytest.fixture
def mock_project_service():
    """Create a mock ProjectService."""
    mock = MagicMock(spec=ProjectService)
    project = Project(
        project_name="Golden Bikes Rental System",
        business_summary="summary",
        requirements=[],
    )
    mock.load_project.return_value = project
    mock.get_project.return_value = project
    return mock


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
        side_effect=lambda conversation_id, user_id, content, type: create_mock_message(
            conversation_id, user_id, content, type
        )
    )
    mock.get_messages_by_conversation_id = AsyncMock(return_value=[])

    return mock


@pytest.fixture
def message_service(mock_message_repository):
    """Create a MessageService with mocked repository."""
    return MessageService(message_repository=mock_message_repository)


@pytest.fixture
def agent_service(mock_persona_service, mock_project_service, mock_message_service):
    """Create an AgentService with mocked dependencies."""
    return AgentService(
        persona_service=mock_persona_service,
        project_service=mock_project_service,
        message_service=mock_message_service,
    )
