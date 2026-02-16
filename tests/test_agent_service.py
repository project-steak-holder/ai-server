"""
Project Steak-Holder

unit tests for agent_service
"""

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


@pytest.mark.skip(
    reason="TODO: Update test after refactoring process_agent_query method"
)
def test_process_agent_query():
    """tests main orchestrator method: process_agent_query()
    TODO: This test needs to be updated to match the new implementation
    """
    pass
