"""
Project Steak-Holder

unit tests for agent_service
"""

from unittest.mock import AsyncMock
import pytest

from src.schemas.persona_model import Persona
from src.schemas.project_model import Project
import uuid


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


@pytest.mark.anyio
async def test_load_history(agent_service):
    """test loading history from message service"""
    user_id = "test_user"
    conversation_id = str(uuid.uuid4())

    history = await agent_service.load_history(
        user_id=user_id, conversation_id=conversation_id
    )

    # Verify message service was called correctly
    agent_service.message_service.get_conversation_history.assert_called_once_with(
        user_id=user_id,
        conversation_id=conversation_id,
    )

    # History should be empty list from mock
    assert history == []


def test_set_request(agent_service):
    """test capturing request"""
    request = "What are the project requirements?"
    agent_service.set_request(request)
    assert agent_service.request == request


@pytest.mark.anyio
async def test_process_agent_query_with_pydantic_ai(agent_service):
    """Test process_agent_query using PydanticAI."""
    from unittest.mock import MagicMock, patch

    user_id = str(uuid.uuid4())
    conversation_id = str(uuid.uuid4())
    content = "What bikes do you have?"

    # Mock the PydanticAI run_stakeholder_query function
    with patch(
        "src.service.agent_service.run_stakeholder_query", new_callable=AsyncMock
    ) as mock_run:
        mock_run.return_value = "We have mountain bikes and road bikes!"

        # Mock message service to return a message
        mock_message = MagicMock()
        mock_message.id = uuid.uuid4()
        mock_message.content = "We have mountain bikes and road bikes!"
        agent_service.message_service.save_ai_message.return_value = mock_message

        # Run the query
        result = await agent_service.process_agent_query(
            user_id=user_id,
            conversation_id=conversation_id,
            content=content,
        )

        # Verify PydanticAI was called
        mock_run.assert_called_once()
        call_kwargs = mock_run.call_args[1]
        assert call_kwargs["message"] == content

        # Verify result structure
        assert result["status"] == "success"
        assert "response" in result


@pytest.mark.anyio
async def test_process_agent_query_handles_llm_error(agent_service):
    """Test process_agent_query handles LLM errors gracefully."""
    from unittest.mock import patch
    from src.exceptions.llm_response_exception import LlmResponseException

    user_id = str(uuid.uuid4())
    conversation_id = str(uuid.uuid4())
    content = "Test message"

    # Mock PydanticAI to raise an exception
    with patch("src.service.agent_service.run_stakeholder_query") as mock_run:
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
