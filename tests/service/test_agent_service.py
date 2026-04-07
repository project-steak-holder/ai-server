"""
Project Steak-Holder

unit tests for agent_service

Note to maintainers:
- Patch apply_delta instead of update_sentiment for all streaming sentiment tests
  (Replace all patch.object(agent_service.sentiment_service, "update_sentiment", ...) with apply_delta)
- And assert on mock_apply_delta.assert_awaited_with(conversation_id, expected_current_sentiment, expected_delta)
- For each test, expected_current_sentiment and expected_delta should match the logic in the test.
"""

import pytest
import uuid
from decimal import Decimal
from unittest.mock import patch, AsyncMock, MagicMock
from src.service.agent_service import LlmResponseException
from pydantic_ai import ModelRequest, ModelResponse, UserPromptPart, TextPart
from src.schemas.persona_model import Persona
from src.schemas.project_model import Project
from src.schemas.message_model import Message, MessageType


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
        import json

        chunks = [
            json.dumps({"content": "We have "}),
            json.dumps({"content": "mountain bikes "}),
            json.dumps({"content": "and road bikes!"}),
        ]
        for chunk in chunks:
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
        patch.object(
            agent_service.sentiment_service,
            "get_persona_w_current_sentiment",
            new=AsyncMock(return_value=agent_service.load_persona()),
        ),
        patch.object(
            agent_service.sentiment_service,
            "get_sentiment",
            new=AsyncMock(return_value=type("Sentiment", (), {"sentiment": 0.0})()),
        ),
        patch.object(
            agent_service.sentiment_service,
            "get_current_sentiment_value",
            new=AsyncMock(return_value=Decimal("0.0")),
        ),
        patch.object(agent_service.sentiment_service, "apply_delta", new=AsyncMock()),
    ):
        # Use real Message objects for mocks to avoid Pydantic validation errors
        from src.schemas.message_model import Message, MessageType

        mock_ai_message = Message(
            id=uuid.uuid4(),
            conversation_id=uuid.UUID(conversation_id),
            content="We have mountain bikes and road bikes!",
            type=MessageType.AI,
        )
        agent_service.message_service.save_ai_message = AsyncMock(
            return_value=mock_ai_message
        )

        mock_user_message = Message(
            id=uuid.uuid4(),
            conversation_id=uuid.UUID(conversation_id),
            content=content,
            type=MessageType.USER,
        )
        agent_service.message_service.save_user_message = AsyncMock(
            return_value=mock_user_message
        )

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
        patch.object(
            agent_service.sentiment_service,
            "get_current_sentiment_value",
            new=AsyncMock(return_value=Decimal("0.0")),
        ),
    ):
        chunks = []
        async for chunk in agent_service.process_agent_query_stream(
            user_id=user_id,
            conversation_id=conversation_id,
            content=content,
        ):
            chunks.append(chunk)

        assert len(chunks) == 1
        assert chunks[0].startswith("data: ")

        import json

        error_data = json.loads(chunks[0][6:-2])  # Remove "data: " and "\n\n"
        assert error_data["content"] == "LLM streaming timeout"

        mock_compact.assert_called_once()
        mock_run_stream.assert_called_once()

        # Verify user message was saved
        agent_service.message_service.save_user_message.assert_called_once_with(
            user_id=user_id, conversation_id=conversation_id, content=content
        )

        # Verify AI error message WAS saved (error responses are now persisted)
        agent_service.message_service.save_ai_message.assert_called_once_with(
            user_id=user_id,
            conversation_id=conversation_id,
            content="LLM streaming timeout",
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
        patch.object(
            agent_service.sentiment_service,
            "get_current_sentiment_value",
            new=AsyncMock(return_value=Decimal("0.0")),
        ),
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
            outcome="test outcome",
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
        import json

        chunks = [
            json.dumps({"content": "Hello "}),
            json.dumps({"content": "there! "}),
            json.dumps({"content": "How "}),
            json.dumps({"content": "are "}),
            json.dumps({"content": "you?"}),
        ]
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
        patch.object(
            agent_service.sentiment_service,
            "get_persona_w_current_sentiment",
            new=AsyncMock(return_value=agent_service.load_persona()),
        ),
        patch.object(
            agent_service.sentiment_service,
            "get_sentiment",
            new=AsyncMock(return_value=type("Sentiment", (), {"sentiment": 0.0})()),
        ),
        patch.object(
            agent_service.sentiment_service,
            "get_current_sentiment_value",
            new=AsyncMock(return_value=Decimal("0.0")),
        ),
        patch.object(agent_service.sentiment_service, "apply_delta", new=AsyncMock()),
    ):
        # Use real Message objects for mocks to avoid Pydantic validation errors
        from src.schemas.message_model import Message, MessageType

        mock_ai_message = Message(
            id=uuid.uuid4(),
            conversation_id=uuid.UUID(conversation_id),
            content="Hello there! How are you?",
            type=MessageType.AI,
        )
        agent_service.message_service.save_ai_message = AsyncMock(
            return_value=mock_ai_message
        )

        mock_user_message = Message(
            id=uuid.uuid4(),
            conversation_id=uuid.UUID(conversation_id),
            content=content,
            type=MessageType.USER,
        )
        agent_service.message_service.save_user_message = AsyncMock(
            return_value=mock_user_message
        )

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
async def test_streaming_sentiment_delta_fallback(agent_service):
    import uuid

    """Streaming: LLM returns no sentiment_delta; backend should fall back to 0.00 and not error."""
    user_id = "user1"
    conversation_id = uuid.uuid4()
    content = "Test message"

    async def mock_stream():
        yield '{"content": "reply", "sentiment": null}'

    with patch(
        "src.service.agent_service._run_stakeholder_query_stream",
        return_value=mock_stream(),
    ):
        with patch.object(
            agent_service.sentiment_service,
            "get_sentiment",
            new=AsyncMock(return_value=type("Sentiment", (), {"sentiment": 5.0})()),
        ):
            with patch.object(
                agent_service.sentiment_service, "apply_delta", new=AsyncMock()
            ) as mock_apply_delta:
                with patch.object(
                    agent_service.message_service, "save_ai_message", new=AsyncMock()
                ) as mock_save:
                    from src.schemas.message_model import Message, MessageType
                    import uuid

                    mock_save.return_value = Message(
                        id=uuid.uuid4(),
                        conversation_id=conversation_id,
                        content="reply",
                        type=MessageType.AI,
                    )
                    with patch.object(
                        agent_service.sentiment_service,
                        "get_current_sentiment_value",
                        new=AsyncMock(return_value=Decimal("5.0")),
                    ):
                        async for _ in agent_service.process_agent_query_stream(
                            user_id=user_id,
                            conversation_id=conversation_id,
                            content=content,
                        ):
                            pass
                        mock_apply_delta.assert_awaited_with(conversation_id, None)


@pytest.mark.anyio
async def test_streaming_sentiment_delta_type_error(agent_service):
    import uuid

    """Streaming: LLM returns non-decimal sentiment_delta; backend should fall back to 0.00."""
    user_id = "user2"
    conversation_id = uuid.uuid4()
    content = "Test message"

    async def mock_stream():
        yield '{"content": "reply", "sentiment": "not_a_number"}'

    with patch(
        "src.service.agent_service._run_stakeholder_query_stream",
        return_value=mock_stream(),
    ):
        with patch.object(
            agent_service.sentiment_service,
            "get_sentiment",
            new=AsyncMock(return_value=type("Sentiment", (), {"sentiment": 2.0})()),
        ):
            with patch.object(
                agent_service.sentiment_service, "apply_delta", new=AsyncMock()
            ) as mock_apply_delta:
                with patch.object(
                    agent_service.message_service, "save_ai_message", new=AsyncMock()
                ) as mock_save:
                    from src.schemas.message_model import Message, MessageType
                    import uuid

                    mock_save.return_value = Message(
                        id=uuid.uuid4(),
                        conversation_id=conversation_id,
                        content="reply",
                        type=MessageType.AI,
                    )
                    with patch.object(
                        agent_service.sentiment_service,
                        "get_current_sentiment_value",
                        new=AsyncMock(return_value=Decimal("2.0")),
                    ):
                        async for _ in agent_service.process_agent_query_stream(
                            user_id=user_id,
                            conversation_id=conversation_id,
                            content=content,
                        ):
                            pass
                        mock_apply_delta.assert_awaited_with(
                            conversation_id, "not_a_number"
                        )


@pytest.mark.anyio
async def test_streaming_sentiment_clamping(agent_service):
    """Streaming: Sentiment update clamps at -10 and +10."""
    user_id = "user3"
    content = "Test message"

    # Clamp upper
    async def mock_stream_upper():
        yield '{"content": "reply", "sentiment": 5.0}'

    with patch(
        "src.service.agent_service._run_stakeholder_query_stream",
        return_value=mock_stream_upper(),
    ):
        with patch.object(
            agent_service.sentiment_service,
            "get_sentiment",
            new=AsyncMock(return_value=type("Sentiment", (), {"sentiment": 8.0})()),
        ):
            with patch.object(
                agent_service.sentiment_service, "apply_delta", new=AsyncMock()
            ) as mock_apply_delta:
                with patch.object(
                    agent_service.message_service, "save_ai_message", new=AsyncMock()
                ) as mock_save:
                    from src.schemas.message_model import Message, MessageType
                    import uuid as uuid_mod

                    conversation_id_upper = uuid_mod.UUID(
                        "00000000-0000-0000-0000-000000000000"
                    )
                    mock_save.return_value = Message(
                        id=uuid_mod.uuid4(),
                        conversation_id=conversation_id_upper,
                        content="reply",
                        type=MessageType.AI,
                    )
                    with patch.object(
                        agent_service.sentiment_service,
                        "get_current_sentiment_value",
                        new=AsyncMock(return_value=Decimal("8.0")),
                    ):
                        async for _ in agent_service.process_agent_query_stream(
                            user_id=user_id,
                            conversation_id=conversation_id_upper,
                            content=content,
                        ):
                            pass
                        mock_apply_delta.assert_awaited_with(conversation_id_upper, 5.0)

    # Clamp lower
    async def mock_stream_lower():
        yield '{"content": "reply", "sentiment": -5.0}'

    with patch(
        "src.service.agent_service._run_stakeholder_query_stream",
        return_value=mock_stream_lower(),
    ):
        with patch.object(
            agent_service.sentiment_service,
            "get_sentiment",
            new=AsyncMock(return_value=type("Sentiment", (), {"sentiment": -8.0})()),
        ):
            with patch.object(
                agent_service.sentiment_service, "apply_delta", new=AsyncMock()
            ) as mock_apply_delta:
                with patch.object(
                    agent_service.message_service, "save_ai_message", new=AsyncMock()
                ) as mock_save:
                    from src.schemas.message_model import Message, MessageType
                    import uuid as uuid_mod

                    conversation_id_lower = uuid_mod.UUID(
                        "00000000-0000-0000-0000-000000000001"
                    )
                    mock_save.return_value = Message(
                        id=uuid_mod.uuid4(),
                        conversation_id=conversation_id_lower,
                        content="reply",
                        type=MessageType.AI,
                    )
                    with patch.object(
                        agent_service.sentiment_service,
                        "get_current_sentiment_value",
                        new=AsyncMock(return_value=Decimal("-8.0")),
                    ):
                        async for _ in agent_service.process_agent_query_stream(
                            user_id=user_id,
                            conversation_id=conversation_id_lower,
                            content=content,
                        ):
                            pass
                        mock_apply_delta.assert_awaited_with(
                            conversation_id_lower, -5.0
                        )


@pytest.mark.anyio
async def test_streaming_absolute_sentiment(agent_service):
    import uuid

    """Streaming: LLM returns absolute sentiment (should be treated as delta, clamped)."""
    user_id = "user5"
    conversation_id = uuid.uuid4()
    content = "Test message"

    async def mock_stream():
        yield '{"content": "reply", "sentiment": 10.0}'

    with patch(
        "src.service.agent_service._run_stakeholder_query_stream",
        return_value=mock_stream(),
    ):
        with patch.object(
            agent_service.sentiment_service,
            "get_sentiment",
            new=AsyncMock(return_value=type("Sentiment", (), {"sentiment": 2.0})()),
        ):
            with patch.object(
                agent_service.sentiment_service, "apply_delta", new=AsyncMock()
            ) as mock_apply_delta:
                with patch.object(
                    agent_service.message_service, "save_ai_message", new=AsyncMock()
                ) as mock_save:
                    from src.schemas.message_model import Message, MessageType
                    import uuid

                    mock_save.return_value = Message(
                        id=uuid.uuid4(),
                        conversation_id=conversation_id,
                        content="reply",
                        type=MessageType.AI,
                    )
                    with patch.object(
                        agent_service.sentiment_service,
                        "get_current_sentiment_value",
                        new=AsyncMock(return_value=Decimal("2.0")),
                    ):
                        async for _ in agent_service.process_agent_query_stream(
                            user_id=user_id,
                            conversation_id=conversation_id,
                            content=content,
                        ):
                            pass
                        mock_apply_delta.assert_awaited_with(conversation_id, 10.0)


@pytest.mark.anyio
async def test_streaming_next_turn_uses_updated_sentiment(agent_service):
    import uuid

    """Streaming: Next turn uses updated sentiment from DB."""
    user_id = "user6"
    conversation_id = uuid.uuid4()
    content = "Test message"

    # First turn: delta +2.0, current 0.0
    async def mock_stream1():
        yield '{"content": "reply", "sentiment": 2.0}'

    with patch(
        "src.service.agent_service._run_stakeholder_query_stream",
        return_value=mock_stream1(),
    ):
        with patch.object(
            agent_service.sentiment_service,
            "get_sentiment",
            new=AsyncMock(return_value=type("Sentiment", (), {"sentiment": 0.0})()),
        ):
            with patch.object(
                agent_service.sentiment_service, "apply_delta", new=AsyncMock()
            ) as mock_apply_delta:
                with patch.object(
                    agent_service.message_service, "save_ai_message", new=AsyncMock()
                ) as mock_save:
                    from src.schemas.message_model import Message, MessageType
                    import uuid

                    mock_save.return_value = Message(
                        id=uuid.uuid4(),
                        conversation_id=conversation_id,
                        content="reply",
                        type=MessageType.AI,
                    )
                    with patch.object(
                        agent_service.sentiment_service,
                        "get_current_sentiment_value",
                        new=AsyncMock(return_value=Decimal("0.0")),
                    ):
                        async for _ in agent_service.process_agent_query_stream(
                            user_id=user_id,
                            conversation_id=conversation_id,
                            content=content,
                        ):
                            pass
                        mock_apply_delta.assert_awaited_with(conversation_id, 2.0)

    # Second turn: delta -1.0, current should be 2.0
    async def mock_stream2():
        yield '{"content": "reply2", "sentiment": -1.0}'

    with patch(
        "src.service.agent_service._run_stakeholder_query_stream",
        return_value=mock_stream2(),
    ):
        with patch.object(
            agent_service.sentiment_service,
            "get_sentiment",
            new=AsyncMock(return_value=type("Sentiment", (), {"sentiment": 2.0})()),
        ):
            with patch.object(
                agent_service.sentiment_service, "apply_delta", new=AsyncMock()
            ) as mock_apply_delta:
                with patch.object(
                    agent_service.message_service, "save_ai_message", new=AsyncMock()
                ) as mock_save:
                    from src.schemas.message_model import Message, MessageType
                    import uuid

                    mock_save.return_value = Message(
                        id=uuid.uuid4(),
                        conversation_id=conversation_id,
                        content="reply2",
                        type=MessageType.AI,
                    )
                    with patch.object(
                        agent_service.sentiment_service,
                        "get_current_sentiment_value",
                        new=AsyncMock(return_value=Decimal("2.0")),
                    ):
                        async for _ in agent_service.process_agent_query_stream(
                            user_id=user_id,
                            conversation_id=conversation_id,
                            content=content,
                        ):
                            pass
                        mock_apply_delta.assert_awaited_with(conversation_id, -1.0)


@pytest.mark.anyio
async def test_streaming_no_cues_delta_zero(agent_service):
    import uuid

    """Streaming: LLM returns delta 0.00 when no cues detected."""
    user_id = "user7"
    conversation_id = uuid.uuid4()
    content = "Test message"

    async def mock_stream():
        yield '{"content": "reply", "sentiment": 0.0}'

    with patch(
        "src.service.agent_service._run_stakeholder_query_stream",
        return_value=mock_stream(),
    ):
        with patch.object(
            agent_service.sentiment_service,
            "get_sentiment",
            new=AsyncMock(return_value=type("Sentiment", (), {"sentiment": 3.0})()),
        ):
            with patch.object(
                agent_service.sentiment_service, "apply_delta", new=AsyncMock()
            ) as mock_apply_delta:
                with patch.object(
                    agent_service.message_service, "save_ai_message", new=AsyncMock()
                ) as mock_save:
                    from src.schemas.message_model import Message, MessageType
                    import uuid

                    mock_save.return_value = Message(
                        id=uuid.uuid4(),
                        conversation_id=conversation_id,
                        content="reply",
                        type=MessageType.AI,
                    )
                    with patch.object(
                        agent_service.sentiment_service,
                        "get_current_sentiment_value",
                        new=AsyncMock(return_value=Decimal("3.0")),
                    ):
                        async for _ in agent_service.process_agent_query_stream(
                            user_id=user_id,
                            conversation_id=conversation_id,
                            content=content,
                        ):
                            pass
                        mock_apply_delta.assert_awaited_with(conversation_id, 0.0)
