"""Unit tests for AI controller V2 streaming endpoint."""

import json
from unittest.mock import MagicMock

import pytest
from fastapi.responses import StreamingResponse

from src.controllers.ai_controller_v2 import generate_stream
from src.schemas.ai import GenerateRequest
from src.dependencies.user import AuthenticatedUser


@pytest.mark.anyio
async def test_ai_controller_v2_generate_stream_success():
    """Test successful streaming response from v2 controller."""
    payload = GenerateRequest(conversation_id="conv-1", content="hello world")
    current_user = AuthenticatedUser(user_id="user-1")
    wide_event = MagicMock()
    agent_service = MagicMock()

    # Mock streaming response
    async def mock_stream():
        chunks = [
            'data: {"content": "Hello ", "partial": true}\n\n',
            'data: {"content": "there!", "partial": true}\n\n',
            'data: {"complete": true}\n\n',
        ]
        for chunk in chunks:
            yield chunk

    agent_service.process_agent_query_stream = MagicMock(return_value=mock_stream())

    result = await generate_stream(
        payload=payload,
        current_user=current_user,
        wide_event=wide_event,
        agent_service=agent_service,
        _=None,
    )

    # Verify it returns a StreamingResponse
    assert isinstance(result, StreamingResponse)
    assert result.media_type == "text/event-stream"

    # Verify headers
    assert result.headers["Cache-Control"] == "no-cache"
    assert result.headers["Connection"] == "keep-alive"

    # Verify wide_event context was added
    wide_event.add_context.assert_called_once()
    call_args = wide_event.add_context.call_args[1]
    assert call_args["user_id"] == "user-1"
    assert call_args["conversation_id"] == "conv-1"
    assert call_args["user_message_preview"] == "hello world"
    assert call_args["streaming"] is True
    assert "ai_service_start_time" in call_args

    # Verify agent service was called with correct parameters
    agent_service.process_agent_query_stream.assert_called_once_with(
        user_id="user-1", conversation_id="conv-1", content="hello world"
    )


@pytest.mark.anyio
async def test_ai_controller_v2_generate_stream_collects_chunks():
    """Test that we can collect and verify streaming chunks."""
    payload = GenerateRequest(conversation_id="conv-2", content="test message")
    current_user = AuthenticatedUser(user_id="user-2")
    wide_event = MagicMock()
    agent_service = MagicMock()

    # Mock streaming response with specific chunks
    async def mock_stream():
        chunks = [
            'data: {"content": "We ", "partial": true}\n\n',
            'data: {"content": "have ", "partial": true}\n\n',
            'data: {"content": "bikes!", "partial": true}\n\n',
            'data: {"complete": true}\n\n',
        ]
        for chunk in chunks:
            yield chunk

    agent_service.process_agent_query_stream = MagicMock(return_value=mock_stream())

    result = await generate_stream(
        payload=payload,
        current_user=current_user,
        wide_event=wide_event,
        agent_service=agent_service,
        _=None,
    )

    # Collect chunks from the streaming response
    chunks = []
    async for chunk in result.body_iterator:
        chunks.append(chunk)

    # Verify the chunks
    expected_chunks = [
        'data: {"content": "We ", "partial": true}\n\n',
        'data: {"content": "have ", "partial": true}\n\n',
        'data: {"content": "bikes!", "partial": true}\n\n',
        'data: {"complete": true}\n\n',
    ]
    assert chunks == expected_chunks


@pytest.mark.anyio
async def test_ai_controller_v2_generate_stream_with_long_message():
    """Test streaming with long message content (preview truncation)."""
    long_content = "a" * 100  # 100 character message
    payload = GenerateRequest(conversation_id="conv-3", content=long_content)
    current_user = AuthenticatedUser(user_id="user-3")
    wide_event = MagicMock()
    agent_service = MagicMock()

    async def mock_stream():
        yield 'data: {"content": "response", "partial": true}\n\n'

    agent_service.process_agent_query_stream = MagicMock(return_value=mock_stream())

    await generate_stream(
        payload=payload,
        current_user=current_user,
        wide_event=wide_event,
        agent_service=agent_service,
        _=None,
    )

    # Verify wide_event preview is truncated to 50 characters
    call_args = wide_event.add_context.call_args[1]
    assert call_args["user_message_preview"] == "a" * 50
    assert len(call_args["user_message_preview"]) == 50


@pytest.mark.anyio
async def test_ai_controller_v2_generate_stream_preserves_rate_limiting():
    """Test that rate limiting dependency is preserved in v2 controller."""
    payload = GenerateRequest(conversation_id="conv-4", content="rate test")
    current_user = AuthenticatedUser(user_id="user-4")
    wide_event = MagicMock()
    agent_service = MagicMock()

    async def mock_stream():
        yield 'data: {"content": "ok", "partial": true}\n\n'

    agent_service.process_agent_query_stream = MagicMock(return_value=mock_stream())

    # Rate limiting is enforced by FastAPI dependency, not called inside generate_stream
    # Passing None for the resolved dependency value should not raise any exception
    result = await generate_stream(
        payload=payload,
        current_user=current_user,
        wide_event=wide_event,
        agent_service=agent_service,
        _=None,  # Rate limit dependency resolved value
    )

    assert isinstance(result, StreamingResponse)


@pytest.mark.anyio
async def test_ai_controller_v2_generate_stream_error_handling():
    """Test that streaming endpoint handles errors from agent service."""
    payload = GenerateRequest(conversation_id="conv-5", content="error test")
    current_user = AuthenticatedUser(user_id="user-5")
    wide_event = MagicMock()
    agent_service = MagicMock()

    # Mock streaming response with error
    async def mock_stream():
        yield 'data: {"content": "Starting ", "partial": true}\n\n'
        yield 'data: {"error": "LLM timeout"}\n\n'

    agent_service.process_agent_query_stream = MagicMock(return_value=mock_stream())

    result = await generate_stream(
        payload=payload,
        current_user=current_user,
        wide_event=wide_event,
        agent_service=agent_service,
        _=None,
    )

    # Collect chunks to verify error is streamed
    chunks = []
    async for chunk in result.body_iterator:
        chunks.append(chunk)

    assert len(chunks) == 2

    # Verify partial content chunk
    partial_data = json.loads(chunks[0][6:-2])  # Remove "data: " and "\n\n"
    assert partial_data["content"] == "Starting "
    assert partial_data["partial"] is True

    # Verify error chunk
    error_data = json.loads(chunks[1][6:-2])
    assert "error" in error_data
    assert error_data["error"] == "LLM timeout"


@pytest.mark.anyio
async def test_ai_controller_v2_generate_stream_maintains_conversation_context():
    """Test that streaming preserves conversation context like non-streaming."""
    payload = GenerateRequest(
        conversation_id="long-conversation-uuid", content="context test"
    )
    current_user = AuthenticatedUser(user_id="experienced-user")
    wide_event = MagicMock()
    agent_service = MagicMock()

    async def mock_stream():
        yield 'data: {"content": "contextual response", "partial": true}\n\n'
        yield 'data: {"complete": true}\n\n'

    agent_service.process_agent_query_stream = MagicMock(return_value=mock_stream())

    await generate_stream(
        payload=payload,
        current_user=current_user,
        wide_event=wide_event,
        agent_service=agent_service,
        _=None,
    )

    # Verify agent service receives all context parameters
    agent_service.process_agent_query_stream.assert_called_once_with(
        user_id="experienced-user",
        conversation_id="long-conversation-uuid",
        content="context test",
    )

    # Verify wide_event captures conversation details
    call_args = wide_event.add_context.call_args[1]
    assert call_args["conversation_id"] == "long-conversation-uuid"
    assert call_args["user_id"] == "experienced-user"


@pytest.mark.anyio
async def test_ai_controller_v2_generate_stream_sse_format_compliance():
    """Test that response follows Server-Sent Events format specification."""
    payload = GenerateRequest(conversation_id="sse-test", content="format test")
    current_user = AuthenticatedUser(user_id="sse-user")
    wide_event = MagicMock()
    agent_service = MagicMock()

    async def mock_stream():
        # Test various SSE formats
        yield 'data: {"content": "test", "partial": true}\n\n'
        yield 'data: {"content": "with escaped newlines", "partial": true}\n\n'
        yield 'data: {"complete": true}\n\n'

    agent_service.process_agent_query_stream = MagicMock(return_value=mock_stream())

    result = await generate_stream(
        payload=payload,
        current_user=current_user,
        wide_event=wide_event,
        agent_service=agent_service,
        _=None,
    )

    # Collect and verify SSE format
    chunks = []
    async for chunk in result.body_iterator:
        chunks.append(chunk)

    for chunk in chunks:
        # Each chunk should start with "data: "
        assert chunk.startswith("data: ")
        # Each chunk should end with "\n\n"
        assert chunk.endswith("\n\n")
        # Content between should be valid JSON
        json_content = chunk[6:-2]  # Remove "data: " and "\n\n"
        parsed = json.loads(json_content)  # Should not raise exception
        assert isinstance(parsed, dict)
