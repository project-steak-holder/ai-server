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
    run_stakeholder_query_stream,
    get_stakeholder_agent,
)
from src.schemas.sentiment_scale_model import SentimentScale, SentimentScaleEntry
from src.schemas.listening_cues_model import ListeningCues, ListeningCue
from src.schemas.instructions_model import InstructionsModel

from src.agents.stakeholder_agent import strip_think_tags


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
        sentiment_scale=dummy_sentiment_scale(),
        listening_cues=dummy_listening_cues(),
        instructions=dummy_instructions(),
    )

    assert deps.persona.name == "Owen"
    assert deps.project.project_name == "Golden Bikes Rental System"
    assert len(deps.history) == 2


def test_agent_response_model():
    """Test AgentResponse Pydantic model validation."""

    # Test default sentiment (should be None)
    response = AgentResponse(content="Hello, I'm Owen!")
    assert response.content == "Hello, I'm Owen!"
    assert response.sentiment is None

    # Test explicit sentiment value
    response_with_sentiment = AgentResponse(content="Hello, I'm Owen!", sentiment=0.75)
    assert response_with_sentiment.content == "Hello, I'm Owen!"
    assert response_with_sentiment.sentiment == 0.75


def test_get_stakeholder_agent_singleton():
    """Test that get_stakeholder_agent returns a singleton."""
    agent1 = get_stakeholder_agent()
    agent2 = get_stakeholder_agent()

    # Should be the same instance
    assert agent1 is agent2


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

        @staticmethod
        def instructions(fn):
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

    # Provide required dummy dependencies for AgentDependencies

    dummy_sentiment_scale = SentimentScale(
        purpose="test", scale=[SentimentScaleEntry(label="neutral", score=0)]
    )
    dummy_listening_cues = ListeningCues(
        purpose="test",
        outcome="test outcome",
        cues={"positive": [ListeningCue(cue="good", score=1.0)]},
    )
    dummy_instructions = InstructionsModel(
        purpose="test",
        precedence=True,
        references=[],
        instructions=["Do something"],
        notes=None,
    )
    ctx = SimpleNamespace(
        deps=AgentDependencies(
            persona=sample_persona,
            project=sample_project,
            history=[],
            sentiment_scale=dummy_sentiment_scale,
            listening_cues=dummy_listening_cues,
            instructions=dummy_instructions,
        )
    )
    prompt_fn = captured["prompt_fn"]
    assert callable(prompt_fn), f"Expected a callable, got {type(prompt_fn)}"
    prompt = prompt_fn(ctx)

    assert f"You are {sample_persona.name}" in prompt
    assert sample_project.project_name in prompt
    assert captured["provider_kwargs"]["base_url"] == "http://ai.local"
    assert captured["model_kwargs"]["model_name"] == "model-x"


@pytest.mark.anyio
async def test_run_stakeholder_query_stream_success(
    sample_persona, sample_project, sample_history
):
    """Test successful stakeholder query streaming execution."""

    # Mock the agent's run_stream method and StreamedRunResult
    mock_streamed_result = MagicMock()

    # Mock the stream_text method to yield chunks
    async def mock_stream_text(delta=None):
        _ = delta
        chunks = ["I think ", "we should ", "focus on ", "quality bikes."]  # noqa: F402
        for chunk in chunks:  # noqa: F402
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
            sentiment_scale=dummy_sentiment_scale(),
            listening_cues=dummy_listening_cues(),
            instructions=dummy_instructions(),
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

    async def mock_stream_text(delta=None):
        _ = delta
        chunks = ["Hello! ", "How can ", "I help?"]  # noqa: F402
        for chunk in chunks:  # noqa: F402
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
            sentiment_scale=dummy_sentiment_scale(),
            listening_cues=dummy_listening_cues(),
            instructions=dummy_instructions(),
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
                sentiment_scale=dummy_sentiment_scale(),
                listening_cues=dummy_listening_cues(),
                instructions=dummy_instructions(),
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

    async def mock_stream_text(delta=None):
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
            sentiment_scale=dummy_sentiment_scale(),
            listening_cues=dummy_listening_cues(),
            instructions=dummy_instructions(),
        ):
            pass

        # Verify stream_text was called with delta=True
        assert len(stream_text_calls) == 1
        assert stream_text_calls[0]["delta"] is True


def test_strip_think_tags():
    # Case 1: Remove <think> tags, preserve whitespace
    text = "Hello <think>internal</think> world!"
    assert strip_think_tags(text) == "Hello  world!"

    # Case 2: Remove <think> tags, strip whitespace
    text = "  <think>internal</think>Trim me  "
    assert strip_think_tags(text, strip_whitespace=True) == "Trim me"

    # Case 3: No <think> tags
    text = "Just normal text."
    assert strip_think_tags(text) == "Just normal text."

    # Case 4: Multiple <think> tags
    text = "A<think>x</think>B<think>y</think>C"
    assert strip_think_tags(text) == "ABC"


def dummy_sentiment_scale():
    return SentimentScale(
        purpose="test", scale=[SentimentScaleEntry(label="neutral", score=0)]
    )


def dummy_listening_cues():
    return ListeningCues(
        purpose="test",
        outcome="test outcome",
        cues={"cue1": [ListeningCue(cue="desc1", score=1.0)]},
    )


def dummy_instructions():
    return InstructionsModel(
        purpose="test", references=[], instructions=["Do X", "Do Y"]
    )
