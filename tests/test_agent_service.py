"""
Project Steak-Holder

unit tests for agent_service
"""

import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pydantic_ai import ModelRequest, ModelResponse, TextPart, UserPromptPart

from src.schemas.persona_model import Persona
from src.schemas.project_model import Project
from src.exceptions.llm_response_exception import LlmResponseException
from src.schemas.message_model import Message, MessageType


@pytest.fixture
def mock_message_service():
    service = AsyncMock()
    service.get_conversation_history = AsyncMock(return_value=mock_history)
    service.save_user_message = AsyncMock()
    service.save_ai_message = AsyncMock()
    return service


def test_load_persona(agent_service):
    """test loading persona from service / default file"""
    persona = agent_service.load_persona()
    assert isinstance(persona, Persona)
    assert persona.name == "Owen"
    assert persona.role == "Owner, Golden Bikes"


def test_load_project(agent_service):
    """test loading project from service / default file"""
    project = agent_service.load_project()
    assert isinstance(project, Project)
    assert project.project_name == "Golden Bikes Rental System"


# Move mock_conversation_id and mock_history here for guaranteed visibility
mock_conversation_id = uuid.uuid4()
mock_history = [
    Message(
        id=uuid.uuid4(),
        conversation_id=mock_conversation_id,
        content="Hello!",
        type=MessageType.USER,
    ),
    Message(
        id=uuid.uuid4(),
        conversation_id=mock_conversation_id,
        content="Hi!",
        type=MessageType.AI,
    ),
]


@pytest.mark.anyio
async def test_load_history(agent_service, mock_message_service):
    """test loading history from message service"""
    user_id = "test_user"
    conversation_id = mock_conversation_id

    mock_message_service.get_conversation_history.return_value = mock_history
    agent_service.message_service = mock_message_service

    history = await agent_service.load_history(user_id=user_id, conversation_id=conversation_id)

    mock_message_service.get_conversation_history.assert_called_once_with(
        user_id=user_id,
        conversation_id=conversation_id,
    )
    assert isinstance(history, list)
    assert all(isinstance(msg, Message) for msg in history)
    assert history == mock_history


def test_set_request(agent_service):
    """test capturing request"""
    request = "What are the project requirements?"
    agent_service.set_request(request)
    assert agent_service.request == request


@pytest.mark.anyio
async def test_process_agent_query_with_pydantic_ai(agent_service):
    """Test process_agent_query using PydanticAI."""
    user_id = str(uuid.uuid4())
    conversation_id = str(uuid.uuid4())
    content = "What bikes do you have?"

    # Prepare a compacted history as ModelRequest/ModelResponse objects
    compacted_history = [
        ModelRequest(parts=[UserPromptPart(content="What bikes do you have?")]),
        ModelResponse(parts=[TextPart(content="We have mountain bikes and road bikes.")]),
    ]

    # Patch the compactor and run_stakeholder_query
    with patch(
        "src.service.history_compactor_service.HistoryCompactorService.summarize_old_messages",
        new_callable=AsyncMock,
        return_value=compacted_history,
    ) as mock_compact:
        # Mock message service to return a message
        mock_message = MagicMock()
        mock_message.id = uuid.uuid4()
        mock_message.content = "We have mountain bikes and road bikes!"
        mock_message.role = "ai"
        agent_service.message_service.save_ai_message.return_value = mock_message

        # Run the query
        result = await agent_service.process_agent_query(
            user_id=user_id,
            conversation_id=conversation_id,
            content=content,
        )

        # Verify compactor was called
        mock_compact.assert_called_once()

        # Check that the compacted history has the correct types
        assert isinstance(compacted_history[0], ModelRequest)
        assert isinstance(compacted_history[1], ModelResponse)
        # Verify result structure
        assert result["status"] == "success"
        assert "response" in result


@pytest.mark.anyio
async def test_process_agent_query_handles_llm_error(agent_service):
    """Test process_agent_query handles LLM errors gracefully."""

    user_id = str(uuid.uuid4())
    conversation_id = str(uuid.uuid4())
    content = "Test message"

    # Patch the compactor to return an empty list
    with patch(
        "src.service.history_compactor_service.HistoryCompactorService.summarize_old_messages",
        new_callable=AsyncMock,
        return_value=[],
    ) as mock_compact, patch(
        "src.service.agent_service.run_stakeholder_query"
    ) as mock_run:
        mock_run.side_effect = LlmResponseException(
            message="LLM timeout", details={"error": "timeout"}
        )

        result = await agent_service.process_agent_query(
            user_id=user_id,
            conversation_id=conversation_id,
            content=content,
        )

        # Should return error event
        assert result["status"] == "error"
        assert "Error processing agent query" in result["response"]
        mock_compact.assert_called_once()
        mock_run.assert_called_once()
