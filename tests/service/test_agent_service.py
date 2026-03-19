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
            "src.service.agent_service.run_stakeholder_query",
            new_callable=AsyncMock,
            return_value="We have mountain bikes and road bikes!",
        ) as mock_run,
    ):
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

        # Verify compactor and agent were called
        mock_compact.assert_called_once()
        mock_run.assert_called_once()

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
    with (
        patch(
            "src.service.history_compactor_service.HistoryCompactorService.summarize_old_messages",
            new_callable=AsyncMock,
            return_value=[],
        ) as mock_compact,
        patch("src.service.agent_service.run_stakeholder_query") as mock_run,
    ):
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
        chunks = ["We have ", "mountain bikes ", "and road bikes!"]
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
            "src.service.agent_service.run_stakeholder_query_stream",
            return_value=mock_streaming_chunks(),
        ) as mock_run_stream,
    ):
        # Mock message service to return a message
        mock_message = MagicMock()
        mock_message.id = uuid.uuid4()
        mock_message.content = "We have mountain bikes and road bikes!"
        mock_message.role = "ai"
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
    """Test process_agent_query_stream handles LLM errors gracefully."""
    user_id = str(uuid.uuid4())
    conversation_id = str(uuid.uuid4())
    content = "Test message"

    # Mock streaming that raises an exception
    async def mock_streaming_error():
        yield "partial chunk"
        # This would be caught by LlmResponseException in the actual streaming function

    # Patch the compactor and streaming function to raise error
    with (
        patch(
            "src.service.history_compactor_service.HistoryCompactorService.summarize_old_messages",
            new_callable=AsyncMock,
            return_value=[],
        ) as mock_compact,
        patch(
            "src.service.agent_service.run_stakeholder_query_stream",
            side_effect=LlmResponseException(
                message="LLM streaming timeout", details={"error": "timeout"}
            ),
        ) as mock_run_stream,
    ):
        # Collect streaming chunks
        chunks = []
        async for chunk in agent_service.process_agent_query_stream(
            user_id=user_id,
            conversation_id=conversation_id,
            content=content,
        ):
            chunks.append(chunk)

        # Should return error event in SSE format
        assert len(chunks) == 1
        assert chunks[0].startswith("data: ")

        import json

        error_data = json.loads(chunks[0][6:-2])  # Remove "data: " and "\n\n"
        assert "error" in error_data

        mock_compact.assert_called_once()
        mock_run_stream.assert_called_once()


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
            "src.service.agent_service.run_stakeholder_query_stream",
            return_value=mock_streaming_chunks(),
        ),
    ):
        # Mock save_ai_message
        mock_message = MagicMock()
        agent_service.message_service.save_ai_message.return_value = mock_message

        # Run streaming
        list(
            [
                chunk
                async for chunk in agent_service.process_agent_query_stream(
                    user_id=user_id,
                    conversation_id=conversation_id,
                    content=content,
                )
            ]
        )

        # Verify context loading methods were called (same as non-streaming)
        assert agent_service.persona_service.load_persona.called
        assert agent_service.project_service.load_project.called

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
            "src.service.agent_service.run_stakeholder_query_stream",
            return_value=mock_streaming_chunks(),
        ),
    ):
        # Mock save_ai_message to capture the full response
        mock_message = MagicMock()
        agent_service.message_service.save_ai_message.return_value = mock_message

        # Run streaming
        list(
            [
                chunk
                async for chunk in agent_service.process_agent_query_stream(
                    user_id=user_id,
                    conversation_id=conversation_id,
                    content=content,
                )
            ]
        )

        # Verify save_ai_message was called with complete accumulated response
        agent_service.message_service.save_ai_message.assert_called_once_with(
            user_id=user_id,
            conversation_id=conversation_id,
            content="Hello there! How are you?",  # All chunks combined
        )
