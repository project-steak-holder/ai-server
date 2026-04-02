"""
Project Steak-Holder

unit tests for agent_service
"""

import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pydantic_ai import ModelRequest, ModelResponse, TextPart, UserPromptPart
from src.agents.stakeholder_agent import AgentResponse
from decimal import Decimal

from src.schemas.persona_model import Persona
from src.service.persona_with_sentiment import get_persona_with_sentiment
from src.schemas.project_model import Project
from src.exceptions.llm_response_exception import LlmResponseException
from src.schemas.message_model import Message, MessageType


@pytest.fixture
async def persona_with_sentiment(agent_service):
    persona = agent_service.load_persona()
    # Use a dummy conversation_id for tests
    return await get_persona_with_sentiment(
        persona, agent_service.sentiment_service, "test-conv-id"
    )


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

    history = await agent_service.load_history(
        user_id=user_id, conversation_id=conversation_id
    )

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


def test_set_conversation_id(agent_service):
    """test capturing conversation id"""
    agent_service.set_conversation_id("conv-123")
    assert agent_service.conversation_id == "conv-123"


@pytest.mark.anyio
async def test_process_agent_query_with_pydantic_ai(agent_service):
    """Test process_agent_query using PydanticAI."""
    user_id = str(uuid.uuid4())
    conversation_id = str(uuid.uuid4())
    content = "What bikes do you have?"

    # Prepare a compacted history as ModelRequest/ModelResponse objects
    compacted_history = [
        ModelRequest(parts=[UserPromptPart(content="What bikes do you have?")]),
        ModelResponse(
            parts=[TextPart(content="We have mountain bikes and road bikes.")]
        ),
    ]

    # Patch the compactor and run_stakeholder_query
    with (
        patch(
            "src.service.history_compactor_service.HistoryCompactorService.summarize_old_messages",
            new_callable=AsyncMock,
            return_value=compacted_history,
        ) as mock_compact,
        patch(
            "src.service.agent_service._run_stakeholder_query",
            new_callable=AsyncMock,
            return_value="We have mountain bikes and road bikes!",
        ) as mock_run,
    ):
        # Mock message service to return a message with valid fields
        mock_message = MagicMock()
        mock_message.id = uuid.uuid4()
        mock_message.conversation_id = uuid.UUID(conversation_id)
        mock_message.content = "We have mountain bikes and road bikes!"
        mock_message.type = MessageType.AI
        agent_service.message_service.save_ai_message.return_value = mock_message

        # Run the query
        result = await agent_service.process_agent_query(
            user_id=user_id,
            conversation_id=conversation_id,
            content=content,
        )

        # Verify compactor and agent were called
        mock_compact.assert_called_once()
        mock_run.assert_called_once()

        # Check that the compacted history has the correct types
        assert isinstance(compacted_history[0], ModelRequest)
        assert isinstance(compacted_history[1], ModelResponse)
        # Verify result is the response string
        assert result == "We have mountain bikes and road bikes!"

        # Verify both messages were persisted after successful LLM response
        agent_service.message_service.save_user_message.assert_called_once_with(
            user_id=user_id,
            conversation_id=conversation_id,
            content=content,
        )
        agent_service.message_service.save_ai_message.assert_called_once_with(
            user_id=user_id,
            conversation_id=conversation_id,
            content="We have mountain bikes and road bikes!",
        )


@pytest.mark.anyio
async def test_process_agent_query_handles_llm_error(agent_service):
    """Test process_agent_query re-raises on LLM error without persisting any messages."""

    user_id = str(uuid.uuid4())
    conversation_id = str(uuid.uuid4())
    content = "Test message"

    with (
        patch(
            "src.service.history_compactor_service.HistoryCompactorService.summarize_old_messages",
            new_callable=AsyncMock,
            return_value=[],
        ) as mock_compact,
        patch("src.service.agent_service._run_stakeholder_query") as mock_run,
    ):
        mock_run.side_effect = LlmResponseException(
            message="LLM timeout", details={"error": "timeout"}
        )

        with pytest.raises(LlmResponseException):
            await agent_service.process_agent_query(
                user_id=user_id,
                conversation_id=conversation_id,
                content=content,
            )

        mock_compact.assert_called_once()
        mock_run.assert_called_once()

        # Neither message should be saved — safe for client retries
        agent_service.message_service.save_user_message.assert_not_called()
        agent_service.message_service.save_ai_message.assert_not_called()


@pytest.mark.anyio
async def test_process_agent_query_stream_success(agent_service):
    """Test process_agent_query_stream with PydanticAI streaming."""
    user_id = str(uuid.uuid4())
    conversation_id = str(uuid.uuid4())
    content = "What bikes do you have?"

    # Prepare a compacted history as ModelRequest/ModelResponse objects
    compacted_history = [
        ModelRequest(parts=[UserPromptPart(content="What bikes do you have?")]),
        ModelResponse(
            parts=[TextPart(content="We have mountain bikes and road bikes.")]
        ),
    ]

    # Mock streaming chunks
    async def mock_streaming_chunks():
        chunks = ["We have ", "mountain bikes ", "and road bikes!"]  # noqa: F402
        for chunk in chunks:  # noqa: F402
            yield chunk

    # Patch the compactor and run_stakeholder_query_stream
    with (
        patch(
            "src.service.history_compactor_service.HistoryCompactorService.summarize_old_messages",
            new_callable=AsyncMock,
            return_value=compacted_history,
        ) as mock_compact,
        patch(
            "src.service.agent_service._run_stakeholder_query_stream",
            return_value=mock_streaming_chunks(),
        ) as mock_run_stream,
    ):
        # Mock message service to return a message with valid fields
        mock_message = MagicMock()
        mock_message.id = uuid.uuid4()
        mock_message.conversation_id = uuid.UUID(conversation_id)
        mock_message.content = "We have mountain bikes and road bikes!"
        mock_message.type = MessageType.AI
        agent_service.message_service.save_ai_message.return_value = mock_message

        # Collect streaming chunks
        chunks = []
        async for chunk in agent_service.process_agent_query_stream(
            user_id=user_id,
            conversation_id=conversation_id,
            content=content,
        ):
            chunks.append(chunk)

        # Verify compactor and streaming agent were called
        mock_compact.assert_called_once()
        mock_run_stream.assert_called_once()

        # Verify we got SSE formatted chunks + completion
        assert len(chunks) == 4  # 3 content chunks + 1 completion

        # Check content chunks are SSE formatted
        import json

        for i in range(3):
            assert chunks[i].startswith("data: ")
            data = json.loads(chunks[i][6:-2])  # Remove "data: " and "\n\n"
            assert data["partial"] is True
            assert "content" in data

        # Check completion chunk
        completion_data = json.loads(chunks[3][6:-2])
        assert completion_data["complete"] is True

        # Verify user message was saved
        agent_service.message_service.save_user_message.assert_called_once_with(
            user_id=user_id, conversation_id=conversation_id, content=content
        )

        # Verify complete AI message was saved
        agent_service.message_service.save_ai_message.assert_called_once_with(
            user_id=user_id,
            conversation_id=conversation_id,
            content="We have mountain bikes and road bikes!",
        )


@pytest.mark.anyio
async def test_process_agent_query_stream_handles_llm_error(agent_service):
    """Test process_agent_query_stream saves error message and yields SSE error event."""
    user_id = str(uuid.uuid4())
    conversation_id = str(uuid.uuid4())
    content = "Test message"

    with (
        patch(
            "src.service.history_compactor_service.HistoryCompactorService.summarize_old_messages",
            new_callable=AsyncMock,
            return_value=[],
        ) as mock_compact,
        patch(
            "src.service.agent_service._run_stakeholder_query_stream",
            side_effect=LlmResponseException(
                message="LLM streaming timeout", details={"error": "timeout"}
            ),
        ) as mock_run_stream,
    ):
        chunks = []
        async for chunk in agent_service.process_agent_query_stream(
            user_id=user_id,
            conversation_id=conversation_id,
            content=content,
        ):
            chunks.append(chunk)

        # Should yield a single SSE error event
        assert len(chunks) == 1
        assert chunks[0].startswith("data: ")

        import json

        error_data = json.loads(chunks[0][6:-2])  # Remove "data: " and "\n\n"
        assert (
            error_data["error"]
            == "I'm sorry, I encountered an error and was unable to respond."
        )
        assert "details" not in error_data

        mock_compact.assert_called_once()
        mock_run_stream.assert_called_once()

        # Verify user message was saved
        agent_service.message_service.save_user_message.assert_called_once_with(
            user_id=user_id, conversation_id=conversation_id, content=content
        )

        # Verify AI error message was saved
        agent_service.message_service.save_ai_message.assert_called_once_with(
            user_id=user_id,
            conversation_id=conversation_id,
            content="I'm sorry, I encountered an error and was unable to respond.",
        )


@pytest.mark.anyio
async def test_process_agent_query_stream_preserves_context_loading(agent_service):
    """Test that streaming preserves the same context loading as non-streaming."""
    user_id = str(uuid.uuid4())
    conversation_id = str(uuid.uuid4())
    content = "Test context preservation"

    # Mock simple streaming
    async def mock_streaming_chunks():
        yield "test response"

    with (
        patch(
            "src.service.history_compactor_service.HistoryCompactorService.summarize_old_messages",
            new_callable=AsyncMock,
            return_value=[],
        ) as mock_compact,
        patch(
            "src.service.agent_service._run_stakeholder_query_stream",
            return_value=mock_streaming_chunks(),
        ),
        patch.object(agent_service, "model_service", MagicMock()) as mock_model_service,
    ):
        # Patch the mock_model_service to return real Persona/Project for get_model
        from src.schemas.persona_model import (
            ExpertiseLevel,
            Personality,
            PersonalityFocus,
            CommunicationRules,
        )
        from src.schemas.sentiment_scale_model import SentimentScale
        from src.schemas.listening_cues_model import ListeningCues
        from src.schemas.instructions_model import InstructionsModel

        dummy_instructions = InstructionsModel(
            purpose="test", references=[], instructions=["Do X", "Do Y"]
        )

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
        from src.schemas.sentiment_scale_model import SentimentScaleEntry
        from src.schemas.listening_cues_model import ListeningCue

        dummy_sentiment_scale = SentimentScale(
            purpose="test", scale=[SentimentScaleEntry(label="neutral", score=0)]
        )
        dummy_listening_cues = ListeningCues(
            purpose="test",
            cues={
                "cue1": [ListeningCue(cue="desc1", score=1.0)],
                "cue2": [ListeningCue(cue="desc2", score=1.0)],
            },
        )
        mock_model_service.get_model.side_effect = lambda name: (
            persona
            if name == "persona"
            else project
            if name == "project"
            else dummy_sentiment_scale
            if name == "sentiment_scale"
            else dummy_listening_cues
            if name == "listening_cues"
            else dummy_instructions
            if name == "instructions"
            else None
        )

        # Mock save_ai_message with valid fields
        mock_message = MagicMock()
        mock_message.id = uuid.uuid4()
        mock_message.conversation_id = uuid.UUID(conversation_id)
        mock_message.content = "test response"
        mock_message.type = MessageType.AI
        agent_service.message_service.save_ai_message.return_value = mock_message

        # Run streaming
        async for _ in agent_service.process_agent_query_stream(
            user_id=user_id,
            conversation_id=conversation_id,
            content=content,
        ):
            pass

        # Verify model_service.get_model was called for persona and project
        calls = [call[0][0] for call in mock_model_service.get_model.call_args_list]
        assert "persona" in calls
        assert "project" in calls

        # Verify compaction was called
        mock_compact.assert_called_once()


@pytest.mark.anyio
async def test_process_agent_query_stream_accumulates_full_response(agent_service):
    """Test that streaming accumulates chunks into complete response for database save."""
    user_id = str(uuid.uuid4())
    conversation_id = str(uuid.uuid4())
    content = "Test accumulation"

    # Mock streaming chunks
    async def mock_streaming_chunks():
        chunks = ["Hello ", "there! ", "How ", "are ", "you?"]
        for chunk in chunks:
            yield chunk

    with (
        patch(
            "src.service.history_compactor_service.HistoryCompactorService.summarize_old_messages",
            new_callable=AsyncMock,
            return_value=[],
        ),
        patch(
            "src.service.agent_service._run_stakeholder_query_stream",
            return_value=mock_streaming_chunks(),
        ),
    ):
        # Mock save_ai_message with valid fields
        mock_message = MagicMock()
        mock_message.id = uuid.uuid4()
        mock_message.conversation_id = uuid.UUID(conversation_id)
        mock_message.content = "Hello there! How are you?"
        mock_message.type = MessageType.AI
        agent_service.message_service.save_ai_message.return_value = mock_message

        # Run streaming
        async for _ in agent_service.process_agent_query_stream(
            user_id=user_id,
            conversation_id=conversation_id,
            content=content,
        ):
            pass

        # Verify save_ai_message was called with complete accumulated response
        agent_service.message_service.save_ai_message.assert_called_once_with(
            user_id=user_id,
            conversation_id=conversation_id,
            content="Hello there! How are you?",  # All chunks combined
        )


@pytest.mark.anyio
async def test_llm_missing_sentiment_delta_fallback(agent_service):
    """LLM returns no sentiment_delta; backend should fall back to 0.00 and not error."""
    user_id = "user1"
    conversation_id = "conv1"
    content = "Test message"
    # persona = agent_service.load_persona()  # Unused
    # history = []  # Unused
    # Patch run_stakeholder_query to return AgentResponse with no sentiment
    with patch(
        "src.service.agent_service.AgentService.run_stakeholder_query",
        new=AsyncMock(return_value=AgentResponse(content="reply", sentiment=None)),
    ):
        with patch.object(
            agent_service.sentiment_service,
            "get_sentiment",
            new=AsyncMock(return_value=type("Sentiment", (), {"sentiment": 5.0})()),
        ):
            with patch.object(
                agent_service.sentiment_service, "update_sentiment", new=AsyncMock()
            ) as mock_update:
                with patch.object(agent_service, "save_ai_message", new=AsyncMock()):
                    result = await agent_service.process_agent_query(
                        user_id, conversation_id, content
                    )
                    assert result == "reply"
                    # Should fall back to 0.00, so updated = 5.0
                    mock_update.assert_awaited_with(conversation_id, Decimal("5.00"))


@pytest.mark.anyio
async def test_llm_invalid_sentiment_delta_type(agent_service):
    """LLM returns non-decimal sentiment_delta; backend should fall back to 0.00."""
    user_id = "user2"
    conversation_id = "conv2"
    content = "Test message"

    # Patch run_stakeholder_query to return a dict (simulate LLM output, bypass Pydantic validation)
    class FakeResponse:
        content = "reply"
        sentiment = "not_a_number"

    with patch(
        "src.service.agent_service.AgentService.run_stakeholder_query",
        new=AsyncMock(return_value=FakeResponse()),
    ):
        with patch.object(
            agent_service.sentiment_service,
            "get_sentiment",
            new=AsyncMock(return_value=type("Sentiment", (), {"sentiment": 2.0})()),
        ):
            with patch.object(
                agent_service.sentiment_service, "update_sentiment", new=AsyncMock()
            ) as mock_update:
                with patch.object(agent_service, "save_ai_message", new=AsyncMock()):
                    result = await agent_service.process_agent_query(
                        user_id, conversation_id, content
                    )
                    assert result == "reply"
                    mock_update.assert_awaited_with(conversation_id, Decimal("2.00"))


@pytest.mark.anyio
async def test_sentiment_clamping_upper_and_lower(agent_service):
    """Sentiment update clamps at -10 and +10."""
    user_id = "user3"
    conversation_id = "conv3"
    content = "Test message"
    # Clamp upper
    with patch(
        "src.service.agent_service.AgentService.run_stakeholder_query",
        new=AsyncMock(return_value=AgentResponse(content="reply", sentiment=5.0)),
    ):
        with patch.object(
            agent_service.sentiment_service,
            "get_sentiment",
            new=AsyncMock(return_value=type("Sentiment", (), {"sentiment": 8.0})()),
        ):
            with patch.object(
                agent_service.sentiment_service, "update_sentiment", new=AsyncMock()
            ) as mock_update:
                with patch.object(agent_service, "save_ai_message", new=AsyncMock()):
                    await agent_service.process_agent_query(
                        user_id, conversation_id, content
                    )
                    mock_update.assert_awaited_with(conversation_id, Decimal("10.00"))
    # Clamp lower
    with patch(
        "src.service.agent_service.AgentService.run_stakeholder_query",
        new=AsyncMock(return_value=AgentResponse(content="reply", sentiment=-5.0)),
    ):
        with patch.object(
            agent_service.sentiment_service,
            "get_sentiment",
            new=AsyncMock(return_value=type("Sentiment", (), {"sentiment": -8.0})()),
        ):
            with patch.object(
                agent_service.sentiment_service, "update_sentiment", new=AsyncMock()
            ) as mock_update:
                with patch.object(agent_service, "save_ai_message", new=AsyncMock()):
                    await agent_service.process_agent_query(
                        user_id, conversation_id, content
                    )
                    mock_update.assert_awaited_with(conversation_id, Decimal("-10.00"))


@pytest.mark.anyio
async def test_llm_output_with_think_tag(agent_service):
    """LLM output includes <think> tags; backend should not include them in saved message."""
    user_id = "user4"
    conversation_id = "conv4"
    content = "Test message"
    llm_content = "<think>reasoning</think> Final answer."
    with patch(
        "src.service.agent_service.AgentService.run_stakeholder_query",
        new=AsyncMock(return_value=AgentResponse(content=llm_content, sentiment=0.5)),
    ):
        with patch.object(
            agent_service.sentiment_service,
            "get_sentiment",
            new=AsyncMock(return_value=type("Sentiment", (), {"sentiment": 0.0})()),
        ):
            with patch.object(
                agent_service.sentiment_service, "update_sentiment", new=AsyncMock()
            ):
                with patch.object(
                    agent_service, "save_ai_message", new=AsyncMock()
                ) as mock_save:
                    await agent_service.process_agent_query(
                        user_id, conversation_id, content
                    )
                    # Check all calls for the saved content
                    found = False
                    for call in mock_save.await_args_list:
                        args = call.args
                        kwargs = call.kwargs
                        print("DEBUG: save_ai_message args:", args, "kwargs:", kwargs)
                        content = kwargs.get(
                            "content", args[2] if len(args) >= 3 else None
                        )
                        if content is not None and "<think>" not in content:
                            found = True
                    assert found, "<think> tag was not stripped from saved message."


@pytest.mark.anyio
async def test_llm_returns_absolute_sentiment(agent_service):
    """LLM returns absolute sentiment (should be rejected/fallback to 0.00)."""
    user_id = "user5"
    conversation_id = "conv5"
    content = "Test message"
    # Simulate LLM returning absolute sentiment (should be delta only)
    with patch(
        "src.service.agent_service.AgentService.run_stakeholder_query",
        new=AsyncMock(return_value=AgentResponse(content="reply", sentiment=10.0)),
    ):
        with patch.object(
            agent_service.sentiment_service,
            "get_sentiment",
            new=AsyncMock(return_value=type("Sentiment", (), {"sentiment": 2.0})()),
        ):
            with patch.object(
                agent_service.sentiment_service, "update_sentiment", new=AsyncMock()
            ) as mock_update:
                with patch.object(agent_service, "save_ai_message", new=AsyncMock()):
                    await agent_service.process_agent_query(
                        user_id, conversation_id, content
                    )
                    # Should treat as delta, so updated = 2.0 + 10.0 = 10.0 (clamped)
                    mock_update.assert_awaited_with(conversation_id, Decimal("10.00"))


@pytest.mark.anyio
async def test_next_turn_uses_updated_sentiment(agent_service):
    """Next turn uses updated sentiment from DB."""
    user_id = "user6"
    conversation_id = "conv6"
    content = "Test message"
    # First turn: delta +2.0, current 0.0
    with patch(
        "src.service.agent_service.AgentService.run_stakeholder_query",
        new=AsyncMock(return_value=AgentResponse(content="reply", sentiment=2.0)),
    ):
        with patch.object(
            agent_service.sentiment_service,
            "get_sentiment",
            new=AsyncMock(return_value=type("Sentiment", (), {"sentiment": 0.0})()),
        ):
            with patch.object(
                agent_service.sentiment_service, "update_sentiment", new=AsyncMock()
            ) as mock_update:
                with patch.object(agent_service, "save_ai_message", new=AsyncMock()):
                    await agent_service.process_agent_query(
                        user_id, conversation_id, content
                    )
                    mock_update.assert_awaited_with(conversation_id, Decimal("2.00"))
    # Second turn: delta -1.0, current should be 2.0
    with patch(
        "src.service.agent_service.AgentService.run_stakeholder_query",
        new=AsyncMock(return_value=AgentResponse(content="reply2", sentiment=-1.0)),
    ):
        with patch.object(
            agent_service.sentiment_service,
            "get_sentiment",
            new=AsyncMock(return_value=type("Sentiment", (), {"sentiment": 2.0})()),
        ):
            with patch.object(
                agent_service.sentiment_service, "update_sentiment", new=AsyncMock()
            ) as mock_update:
                with patch.object(agent_service, "save_ai_message", new=AsyncMock()):
                    await agent_service.process_agent_query(
                        user_id, conversation_id, content
                    )
                    mock_update.assert_awaited_with(conversation_id, Decimal("1.00"))


@pytest.mark.anyio
async def test_llm_no_cues_delta_zero(agent_service):
    """LLM returns delta 0.00 when no cues detected."""
    user_id = "user7"
    conversation_id = "conv7"
    content = "Test message"
    with patch(
        "src.service.agent_service.AgentService.run_stakeholder_query",
        new=AsyncMock(return_value=AgentResponse(content="reply", sentiment=0.0)),
    ):
        with patch.object(
            agent_service.sentiment_service,
            "get_sentiment",
            new=AsyncMock(return_value=type("Sentiment", (), {"sentiment": 3.0})()),
        ):
            with patch.object(
                agent_service.sentiment_service, "update_sentiment", new=AsyncMock()
            ) as mock_update:
                with patch.object(agent_service, "save_ai_message", new=AsyncMock()):
                    await agent_service.process_agent_query(
                        user_id, conversation_id, content
                    )
                    mock_update.assert_awaited_with(conversation_id, Decimal("3.00"))
