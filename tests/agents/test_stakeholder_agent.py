"""
Unit tests for PydanticAI Stakeholder Agent.
"""

import pytest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from pydantic_ai import ModelRequest, ModelResponse, UserPromptPart, TextPart

from src.agents.stakeholder_agent import (
    AgentDependencies,
    AgentResponse,
    create_stakeholder_agent,
    run_stakeholder_query,
    run_stakeholder_query_stream,
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
        ModelResponse(
            parts=[TextPart(content="We have mountain bikes and road bikes.")]
        ),
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

        # Check the user_prompt argument
        assert call_args[1]["user_prompt"] == "What should we prioritize?"

        # Check the deps argument
        deps = call_args[1]["deps"]
        assert isinstance(deps, AgentDependencies)
        assert deps.persona == sample_persona
        assert deps.project == sample_project
        assert deps.history == sample_history


@pytest.mark.anyio
async def test_run_stakeholder_query_with_empty_history(sample_persona, sample_project):
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


def test_create_stakeholder_agent_builds_prompt(
    monkeypatch, sample_persona, sample_project
):
    """Test agent creation wiring and generated system prompt."""
    captured = {}

    class FakeProvider:
        def __init__(self, **kwargs):
            captured["provider_kwargs"] = kwargs

    class FakeModel:
        def __init__(self, **kwargs):
            captured["model_kwargs"] = kwargs

    class FakeAgent:
        @classmethod
        def __class_getitem__(cls, _item):
            return cls

        def __init__(self, **kwargs):
            captured["agent_kwargs"] = kwargs

        def instructions(self, fn):
            captured["prompt_fn"] = fn
            return fn

    monkeypatch.setenv("AI_PROVIDER_BASE_URL", "http://ai.local")
    monkeypatch.setenv("AI_PROVIDER_API_KEY", "key")
    monkeypatch.setenv("AI_PROVIDER_MODEL", "model-x")
    monkeypatch.setattr("src.agents.stakeholder_agent.OpenAIProvider", FakeProvider)
    monkeypatch.setattr("src.agents.stakeholder_agent.OpenAIChatModel", FakeModel)
    monkeypatch.setattr("src.agents.stakeholder_agent.Agent", FakeAgent)

    agent = create_stakeholder_agent()
    assert isinstance(agent, FakeAgent)

    ctx = SimpleNamespace(
        deps=AgentDependencies(
            persona=sample_persona, project=sample_project, history=[]
        )
    )
    prompt = captured["prompt_fn"](ctx)

    assert f"You are {sample_persona.name}" in prompt
    assert sample_project.project_name in prompt
    assert captured["provider_kwargs"]["base_url"] == "http://ai.local"
    assert captured["model_kwargs"]["model_name"] == "model-x"


@pytest.mark.anyio
async def test_run_stakeholder_query_wraps_unexpected_exception(
    sample_persona, sample_project
):
    """Test non-LLM exceptions are wrapped as LlmResponseException."""
    with patch("src.agents.stakeholder_agent.get_stakeholder_agent") as mock_get_agent:
        mock_agent = MagicMock()
        mock_agent.run = AsyncMock(side_effect=RuntimeError("llm down"))
        mock_get_agent.return_value = mock_agent

        with pytest.raises(Exception, match="Error running stakeholder agent"):
            await run_stakeholder_query(
                message="hello",
                persona=sample_persona,
                project=sample_project,
                history=[],
            )


@pytest.mark.anyio
async def test_run_stakeholder_query_stream_success(
    sample_persona, sample_project, sample_history
):
    """Test successful stakeholder query streaming execution."""

    # Mock the agent's run_stream method and StreamedRunResult
    mock_streamed_result = MagicMock()

    # Mock the stream_text method to yield chunks
    async def mock_stream_text(delta=True):
        chunks = ["I think ", "we should ", "focus on ", "quality bikes."]
        for chunk in chunks:
            yield chunk

    mock_streamed_result.stream_text = mock_stream_text

    with patch("src.agents.stakeholder_agent.get_stakeholder_agent") as mock_get_agent:
        mock_agent = MagicMock()
        mock_cm = MagicMock()
        mock_cm.__aenter__ = AsyncMock(return_value=mock_streamed_result)
        mock_cm.__aexit__ = AsyncMock(return_value=False)
        mock_agent.run_stream = MagicMock(return_value=mock_cm)
        mock_get_agent.return_value = mock_agent

        # Run the streaming query
        chunks = []
        async for chunk in run_stakeholder_query_stream(
            message="What should we prioritize?",
            persona=sample_persona,
            project=sample_project,
            history=sample_history,
        ):
            chunks.append(chunk)

        # Verify the chunks
        expected_chunks = ["I think ", "we should ", "focus on ", "quality bikes."]
        assert chunks == expected_chunks

        # Verify agent.run_stream was called with correct args
        mock_agent.run_stream.assert_called_once()
        call_args = mock_agent.run_stream.call_args

        # Check the user_prompt argument
        assert call_args[1]["user_prompt"] == "What should we prioritize?"

        # Check output_type override for text streaming
        assert call_args[1]["output_type"] is str

        # Check the deps argument
        deps = call_args[1]["deps"]
        assert isinstance(deps, AgentDependencies)
        assert deps.persona == sample_persona
        assert deps.project == sample_project
        assert deps.history == sample_history


@pytest.mark.anyio
async def test_run_stakeholder_query_stream_with_empty_history(
    sample_persona, sample_project
):
    """Test stakeholder query streaming with no conversation history."""

    mock_streamed_result = MagicMock()

    async def mock_stream_text(delta=True):
        chunks = ["Hello! ", "How can ", "I help?"]
        for chunk in chunks:
            yield chunk

    mock_streamed_result.stream_text = mock_stream_text

    with patch("src.agents.stakeholder_agent.get_stakeholder_agent") as mock_get_agent:
        mock_agent = MagicMock()
        mock_cm = MagicMock()
        mock_cm.__aenter__ = AsyncMock(return_value=mock_streamed_result)
        mock_cm.__aexit__ = AsyncMock(return_value=False)
        mock_agent.run_stream = MagicMock(return_value=mock_cm)
        mock_get_agent.return_value = mock_agent

        # Run with empty history
        chunks = []
        async for chunk in run_stakeholder_query_stream(
            message="Hi there!",
            persona=sample_persona,
            project=sample_project,
            history=[],
        ):
            chunks.append(chunk)

        expected_chunks = ["Hello! ", "How can ", "I help?"]
        assert chunks == expected_chunks

        # Verify deps had empty history
        deps = mock_agent.run_stream.call_args[1]["deps"]
        assert deps.history == []


@pytest.mark.anyio
async def test_run_stakeholder_query_stream_wraps_unexpected_exception(
    sample_persona, sample_project
):
    """Test streaming function wraps unexpected exceptions as LlmResponseException."""

    with patch("src.agents.stakeholder_agent.get_stakeholder_agent") as mock_get_agent:
        mock_agent = MagicMock()
        mock_cm = MagicMock()
        mock_cm.__aenter__ = AsyncMock(side_effect=RuntimeError("llm streaming down"))
        mock_cm.__aexit__ = AsyncMock(return_value=False)
        mock_agent.run_stream = MagicMock(return_value=mock_cm)
        mock_get_agent.return_value = mock_agent

        with pytest.raises(
            Exception, match="Error streaming stakeholder agent response"
        ):
            async for _ in run_stakeholder_query_stream(
                message="hello",
                persona=sample_persona,
                project=sample_project,
                history=[],
            ):
                pass


@pytest.mark.anyio
async def test_run_stakeholder_query_stream_preserves_streaming_parameters(
    sample_persona, sample_project
):
    """Test that streaming query uses delta=True for incremental chunks."""

    mock_streamed_result = MagicMock()

    # Track the parameters passed to stream_text
    stream_text_calls = []

    async def mock_stream_text(delta=True):
        stream_text_calls.append({"delta": delta})
        yield "test chunk"

    mock_streamed_result.stream_text = mock_stream_text

    with patch("src.agents.stakeholder_agent.get_stakeholder_agent") as mock_get_agent:
        mock_agent = MagicMock()
        mock_cm = MagicMock()
        mock_cm.__aenter__ = AsyncMock(return_value=mock_streamed_result)
        mock_cm.__aexit__ = AsyncMock(return_value=False)
        mock_agent.run_stream = MagicMock(return_value=mock_cm)
        mock_get_agent.return_value = mock_agent

        # Run the streaming query
        async for _ in run_stakeholder_query_stream(
            message="test",
            persona=sample_persona,
            project=sample_project,
            history=[],
        ):
            pass

        # Verify stream_text was called with delta=True
        assert len(stream_text_calls) == 1
        assert stream_text_calls[0]["delta"] is True
