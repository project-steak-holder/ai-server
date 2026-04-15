"""
Project Steak-Holder

unit tests for agent_service
"""

import pytest
import uuid

from unittest.mock import patch, AsyncMock, MagicMock
from src.exceptions.llm_response_exception import LlmResponseException
from pydantic_ai import ModelResponse
from src.schemas.persona_model import Persona
from src.schemas.project_model import Project
from src.schemas.message_model import Message, MessageType
from src.schemas.listening_cues_model import ListeningCue


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


@pytest.mark.anyio
async def test_process_agent_query_stream_success(agent_service):
    """Test process_agent_query_stream with PydanticAI streaming."""
    user_id = str(uuid.uuid4())
    conversation_id = str(uuid.uuid4())
    content = "What bikes do you have?"

    # Mock streaming chunks as AgentResponse objects
    from src.agents.stakeholder_agent import AgentResponse

    async def mock_streaming_chunks():
        chunks = [
            AgentResponse(content="We have "),
            AgentResponse(content="mountain bikes "),
            AgentResponse(content="and road bikes!"),
        ]
        for chunk in chunks:
            yield chunk

    with (
        patch(
            "src.service.agent_service._run_stakeholder_query_stream",
            return_value=mock_streaming_chunks(),
        ) as mock_run_stream,
        patch(
            "src.service.agent_service.convert_messages_to_model_messages",
            return_value=[],
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
            new=AsyncMock(return_value=0.0),
        ),
        patch.object(agent_service.sentiment_service, "apply_delta", new=AsyncMock()),
    ):
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

        # Verify summary repo was queried and streaming agent was called
        agent_service.summary_service.summary_repository.get_conversation_summary.assert_called_once()
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
            "src.service.agent_service._run_stakeholder_query_stream",
            side_effect=LlmResponseException(
                message="LLM streaming timeout", details={"error": "timeout"}
            ),
        ) as mock_run_stream,
        patch(
            "src.service.agent_service.convert_messages_to_model_messages",
            return_value=[],
        ),
        patch.object(
            agent_service.sentiment_service,
            "get_current_sentiment_value",
            new=AsyncMock(return_value=0.0),
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
        assert (
            error_data["content"]
            == "I'm sorry, I encountered an unexpected error and was unable to respond."
        )
        assert error_data["error"] is True
        assert error_data["complete"] is True

        agent_service.summary_service.summary_repository.get_conversation_summary.assert_called_once()
        mock_run_stream.assert_called_once()

        # Verify user message was saved
        agent_service.message_service.save_user_message.assert_called_once_with(
            user_id=user_id, conversation_id=conversation_id, content=content
        )

        # Verify AI error message WAS saved (error responses are now persisted)
        agent_service.message_service.save_ai_message.assert_called_once_with(
            user_id=user_id,
            conversation_id=conversation_id,
            content="I'm sorry, I encountered an unexpected error and was unable to respond.",
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
            "src.service.agent_service._run_stakeholder_query_stream",
            return_value=mock_streaming_chunks(),
        ),
        patch(
            "src.service.agent_service.convert_messages_to_model_messages",
            return_value=[],
        ),
        patch.object(agent_service, "model_service", MagicMock()) as mock_model_service,
        patch.object(
            agent_service.sentiment_service,
            "get_current_sentiment_value",
            new=AsyncMock(return_value=0.0),
        ),
    ):
        # Patch the mock_model_service to return real Persona/Project for get_model
        from src.schemas.persona_model import (
            Persona,
            ExpertiseLevel,
            Personality,
            PersonalityFocus,
            CommunicationRules,
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
        from src.schemas.sentiment_scale_model import (
            SentimentScale,
            SentimentScaleEntry,
        )
        from src.schemas.listening_cues_model import ListeningCues
        from src.schemas.instructions_model import InstructionsModel

        dummy_instructions = InstructionsModel(
            purpose="test", references=[], instructions=["Do X", "Do Y"]
        )

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
        mock_model_service.get_model.side_effect = lambda name, expected_type=None: (
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

        # Verify model_service.get_model was called for project
        calls = [call[0][0] for call in mock_model_service.get_model.call_args_list]
        assert "project" in calls

        # Verify summary repo was queried
        agent_service.summary_service.summary_repository.get_conversation_summary.assert_called_once()


@pytest.mark.anyio
async def test_process_agent_query_stream_accumulates_full_response(agent_service):
    """Test that streaming accumulates chunks into complete response for database save."""
    user_id = str(uuid.uuid4())
    conversation_id = str(uuid.uuid4())
    content = "Test accumulation"

    # Mock streaming chunks as AgentResponse objects
    from src.agents.stakeholder_agent import AgentResponse

    async def mock_streaming_chunks():
        chunks = [
            AgentResponse(content="Hello "),
            AgentResponse(content="there! "),
            AgentResponse(content="How "),
            AgentResponse(content="are "),
            AgentResponse(content="you?"),
        ]
        for chunk in chunks:
            yield chunk

    with (
        patch(
            "src.service.agent_service._run_stakeholder_query_stream",
            return_value=mock_streaming_chunks(),
        ),
        patch(
            "src.service.agent_service.convert_messages_to_model_messages",
            return_value=[],
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
            new=AsyncMock(return_value=0.0),
        ),
        patch.object(agent_service.sentiment_service, "apply_delta", new=AsyncMock()),
    ):
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
async def test_streaming_sentiment_absolute(agent_service):
    """Streaming: LLM returns absolute sentiment (should persist it directly)."""
    user_id = "user5"
    conversation_id = uuid.uuid4()
    content = "Test message"

    from src.agents.stakeholder_agent import AgentResponse
    from src.schemas.persona_model import (
        Persona,
        ExpertiseLevel,
        Personality,
        PersonalityFocus,
        CommunicationRules,
    )

    async def mock_stream():
        yield AgentResponse(content="reply", sentiment=10.0)

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
    mock_ai_msg = Message(
        id=uuid.uuid4(),
        conversation_id=conversation_id,
        content="reply",
        type=MessageType.AI,
    )

    with (
        patch(
            "src.service.agent_service._run_stakeholder_query_stream",
            return_value=mock_stream(),
        ),
        patch(
            "src.service.agent_service.convert_messages_to_model_messages",
            return_value=[],
        ),
        patch.object(
            agent_service.sentiment_service,
            "get_persona_w_current_sentiment",
            new=AsyncMock(return_value=persona),
        ),
        patch.object(
            agent_service.message_service,
            "save_ai_message",
            new=AsyncMock(return_value=mock_ai_msg),
        ),
        patch.object(
            agent_service.sentiment_service,
            "update_sentiment",
            new=AsyncMock(),
        ) as mock_update_sentiment,
    ):
        async for _ in agent_service.process_agent_query_stream(
            user_id=user_id,
            conversation_id=conversation_id,
            content=content,
        ):
            pass
        mock_update_sentiment.assert_awaited_with(
            conversation_id=conversation_id, new_value=10.0
        )


@pytest.mark.anyio
async def test_streaming_next_turn_uses_updated_sentiment(agent_service):
    """Streaming: Next turn uses updated sentiment from DB."""
    user_id = "user6"
    conversation_id = uuid.uuid4()
    content = "Test message"

    from src.agents.stakeholder_agent import AgentResponse
    from src.schemas.persona_model import (
        Persona,
        ExpertiseLevel,
        Personality,
        PersonalityFocus,
        CommunicationRules,
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

    # First turn: agent returns absolute sentiment 2.0
    async def mock_stream1():
        yield AgentResponse(content="reply", sentiment=2.0)

    mock_ai_msg1 = Message(
        id=uuid.uuid4(),
        conversation_id=conversation_id,
        content="reply",
        type=MessageType.AI,
    )

    with (
        patch(
            "src.service.agent_service._run_stakeholder_query_stream",
            return_value=mock_stream1(),
        ),
        patch(
            "src.service.agent_service.convert_messages_to_model_messages",
            return_value=[],
        ),
        patch.object(
            agent_service.sentiment_service,
            "get_persona_w_current_sentiment",
            new=AsyncMock(return_value=persona),
        ),
        patch.object(
            agent_service.message_service,
            "save_ai_message",
            new=AsyncMock(return_value=mock_ai_msg1),
        ),
        patch.object(
            agent_service.sentiment_service,
            "update_sentiment",
            new=AsyncMock(),
        ) as mock_update_sentiment,
    ):
        async for _ in agent_service.process_agent_query_stream(
            user_id=user_id,
            conversation_id=conversation_id,
            content=content,
        ):
            pass
        mock_update_sentiment.assert_awaited_with(
            conversation_id=conversation_id, new_value=2.0
        )

    # Second turn: agent returns absolute sentiment -1.0
    async def mock_stream2():
        yield AgentResponse(content="reply2", sentiment=-1.0)

    mock_ai_msg2 = Message(
        id=uuid.uuid4(),
        conversation_id=conversation_id,
        content="reply2",
        type=MessageType.AI,
    )

    with (
        patch(
            "src.service.agent_service._run_stakeholder_query_stream",
            return_value=mock_stream2(),
        ),
        patch(
            "src.service.agent_service.convert_messages_to_model_messages",
            return_value=[],
        ),
        patch.object(
            agent_service.sentiment_service,
            "get_persona_w_current_sentiment",
            new=AsyncMock(return_value=persona),
        ),
        patch.object(
            agent_service.message_service,
            "save_ai_message",
            new=AsyncMock(return_value=mock_ai_msg2),
        ),
        patch.object(
            agent_service.sentiment_service,
            "update_sentiment",
            new=AsyncMock(),
        ) as mock_update_sentiment,
    ):
        async for _ in agent_service.process_agent_query_stream(
            user_id=user_id,
            conversation_id=conversation_id,
            content=content,
        ):
            pass
        mock_update_sentiment.assert_awaited_with(
            conversation_id=conversation_id, new_value=-1.0
        )


@pytest.mark.anyio
async def test_process_agent_query_stream_uses_cached_summary(agent_service):
    """Test that cached summary content is prepended to history."""
    user_id = str(uuid.uuid4())
    conversation_id = str(uuid.uuid4())
    content = "Test with summary"

    from src.agents.stakeholder_agent import AgentResponse

    async def mock_stream():
        yield AgentResponse(content="response")

    # Set up a cached summary
    mock_summary = MagicMock()
    mock_summary.content = "Previous conversation summary"
    agent_service.summary_service.summary_repository.get_conversation_summary = (
        AsyncMock(return_value=mock_summary)
    )

    with (
        patch(
            "src.service.agent_service._run_stakeholder_query_stream",
            return_value=mock_stream(),
        ) as mock_run_stream,
        patch(
            "src.service.agent_service.convert_messages_to_model_messages",
            return_value=[],
        ),
        patch.object(
            agent_service.sentiment_service,
            "get_persona_w_current_sentiment",
            new=AsyncMock(return_value=agent_service.load_persona()),
        ),
        patch.object(
            agent_service.sentiment_service,
            "get_current_sentiment_value",
            new=AsyncMock(return_value=0.0),
        ),
    ):
        mock_ai_msg = Message(
            id=uuid.uuid4(),
            conversation_id=uuid.UUID(conversation_id),
            content="response",
            type=MessageType.AI,
        )
        agent_service.message_service.save_ai_message = AsyncMock(
            return_value=mock_ai_msg
        )

        async for _ in agent_service.process_agent_query_stream(
            user_id=user_id,
            conversation_id=conversation_id,
            content=content,
        ):
            pass

        # Verify the history passed to the streaming agent includes the summary
        call_kwargs = mock_run_stream.call_args.kwargs
        history = call_kwargs["history"]
        assert len(history) >= 1
        assert isinstance(history[0], ModelResponse)
        assert history[0].parts[0].content == "Previous conversation summary"  # type: ignore[union-attr]
