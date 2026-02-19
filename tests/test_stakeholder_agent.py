"""
Unit tests for PydanticAI Stakeholder Agent.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pydantic_ai import ModelRequest, ModelResponse, UserPromptPart, TextPart

from src.agents.stakeholder_agent import (
    AgentDependencies,
    AgentResponse,
    run_stakeholder_query,
    get_stakeholder_agent,
)
from src.schemas.persona_model import Persona
from src.schemas.project_model import Project


@pytest.fixture
def sample_persona():
    """Create a sample persona for testing."""
    from src.schemas.persona_model import (
        ExpertiseLevel,
        Personality,
        PersonalityFocus,
        CommunicationRules,
    )

    return Persona(
        name="Owen",
        role="Owner, Golden Bikes",
        location="San Francisco",
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
    """Create a sample project for testing."""
    return Project(
        project_name="Golden Bikes Rental System",
        business_summary="A bike rental platform for urban commuters",
        requirements=[],
    )


@pytest.fixture
def sample_history():
    """Create sample conversation history."""
    return [
        ModelRequest(parts=[UserPromptPart(content="What bikes do you have?")]),
        ModelResponse(parts=[TextPart(content="We have mountain bikes and road bikes.")])
    ]


def test_agent_dependencies_model(sample_persona, sample_project, sample_history):
    """Test AgentDependencies Pydantic model validation."""
    deps = AgentDependencies(
        persona=sample_persona,
        project=sample_project,
        history=sample_history,
    )

    assert deps.persona.name == "Owen"
    assert deps.project.project_name == "Golden Bikes Rental System"
    assert len(deps.history) == 2


def test_agent_response_model():
    """Test AgentResponse Pydantic model validation."""
    response = AgentResponse(content="Hello, I'm Owen!")

    assert response.content == "Hello, I'm Owen!"


def test_get_stakeholder_agent_singleton():
    """Test that get_stakeholder_agent returns a singleton."""
    agent1 = get_stakeholder_agent()
    agent2 = get_stakeholder_agent()

    # Should be the same instance
    assert agent1 is agent2


@pytest.mark.anyio
async def test_run_stakeholder_query_success(
    sample_persona, sample_project, sample_history
):
    """Test successful stakeholder query execution."""

    # Mock the agent's run method result
    mock_result = MagicMock()
    mock_response = AgentResponse(content="I think we should focus on quality bikes.")
    mock_result.output = mock_response

    with patch("src.agents.stakeholder_agent.get_stakeholder_agent") as mock_get_agent:
        mock_agent = MagicMock()
        mock_agent.run = AsyncMock(return_value=mock_result)
        mock_get_agent.return_value = mock_agent

        # Run the query
        result = await run_stakeholder_query(
            message="What should we prioritize?",
            persona=sample_persona,
            project=sample_project,
            history=sample_history,
        )

        # Verify the result
        assert result == "I think we should focus on quality bikes."

        # Verify agent.run was called with correct args
        mock_agent.run.assert_called_once()
        call_args = mock_agent.run.call_args

        # Check the message argument
        assert call_args[0][0] == "What should we prioritize?"

        # Check the deps argument
        deps = call_args[1]["deps"]
        assert isinstance(deps, AgentDependencies)
        assert deps.persona == sample_persona
        assert deps.project == sample_project
        assert deps.history == sample_history


@pytest.mark.anyio
async def test_run_stakeholder_query_with_empty_history(
    sample_persona, sample_project
):
    """Test stakeholder query with no conversation history."""

    mock_result = MagicMock()
    mock_response = AgentResponse(content="Hello! How can I help?")
    mock_result.output = mock_response

    with patch("src.agents.stakeholder_agent.get_stakeholder_agent") as mock_get_agent:
        mock_agent = MagicMock()
        mock_agent.run = AsyncMock(return_value=mock_result)
        mock_get_agent.return_value = mock_agent

        # Run with empty history
        result = await run_stakeholder_query(
            message="Hi there!",
            persona=sample_persona,
            project=sample_project,
            history=[],
        )

        assert result == "Hello! How can I help?"

        # Verify deps had empty history
        deps = mock_agent.run.call_args[1]["deps"]
        assert deps.history == []


@pytest.mark.anyio
async def test_run_stakeholder_query_preserves_persona_characteristics(
    sample_persona, sample_project
):
    """Test that query preserves persona characteristics in dependencies."""

    mock_result = MagicMock()
    mock_response = AgentResponse(content="As a business owner, I think...")
    mock_result.output = mock_response

    with patch("src.agents.stakeholder_agent.get_stakeholder_agent") as mock_get_agent:
        mock_agent = MagicMock()
        mock_agent.run = AsyncMock(return_value=mock_result)
        mock_get_agent.return_value = mock_agent

        await run_stakeholder_query(
            message="What's your expertise?",
            persona=sample_persona,
            project=sample_project,
            history=[],
        )

        # Verify persona details are preserved
        deps = mock_agent.run.call_args[1]["deps"]
        assert deps.persona.expertise_level.business == "high"
        assert deps.persona.personality.professionalism == "business casual"
        assert "technical jargon" in deps.persona.communication_rules.avoid
