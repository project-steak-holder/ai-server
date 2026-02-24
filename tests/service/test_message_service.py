"""
Unit tests for MessageService.
"""

import pytest
import uuid

from src.schemas.message_model import MessageType


@pytest.mark.anyio
async def test_save_user_message(message_service, mock_message_repository):
    """Test saving a user message."""
    conversation_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    content = "Hello, this is a user message"

    # Call the service method
    result = await message_service.save_user_message(
        conversation_id=conversation_id,
        user_id=user_id,
        content=content,
    )

    # Verify repository was called with correct parameters
    mock_message_repository.save_message.assert_called_once_with(
        conversation_id=conversation_id,
        user_id=user_id,
        content=content,
        type=MessageType.USER,
    )

    # Verify the result
    assert result.content == content
    assert result.type == MessageType.USER
    assert str(result.user_id) == user_id


@pytest.mark.anyio
async def test_save_ai_message(message_service, mock_message_repository):
    """Test saving an AI message."""
    conversation_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    content = "Hello, this is an AI response"

    # Call the service method
    result = await message_service.save_ai_message(
        conversation_id=conversation_id,
        user_id=user_id,
        content=content,
    )

    # Verify repository was called with correct parameters
    mock_message_repository.save_message.assert_called_once_with(
        conversation_id=conversation_id,
        user_id=user_id,
        content=content,
        type=MessageType.AI,
    )

    # Verify the result
    assert result.content == content
    assert result.type == MessageType.AI
    assert str(result.user_id) == user_id


@pytest.mark.anyio
async def test_get_conversation_history(message_service, mock_message_repository):
    """Test retrieving conversation history."""
    conversation_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())

    # Call the service method
    result = await message_service.get_conversation_history(
        conversation_id=conversation_id,
        user_id=user_id,
    )

    # Verify repository was called with correct parameters
    mock_message_repository.get_messages_by_conversation_id.assert_called_once_with(
        conversation_id=conversation_id,
        user_id=user_id,
    )

    # Verify the result (should be empty list from mock)
    assert isinstance(result, list)
    assert len(result) == 0


@pytest.mark.anyio
async def test_get_conversation_history_with_messages(
    message_service, mock_message_repository
):
    """Test retrieving conversation history with existing messages."""
    from unittest.mock import MagicMock
    from datetime import datetime, timezone

    conversation_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())

    # Create mock messages
    msg1 = MagicMock()
    msg1.id = uuid.uuid4()
    msg1.conversation_id = uuid.UUID(conversation_id)
    msg1.user_id = uuid.UUID(user_id)
    msg1.content = "User message"
    msg1.type = MessageType.USER
    msg1.created_at = datetime.now(timezone.utc)

    msg2 = MagicMock()
    msg2.id = uuid.uuid4()
    msg2.conversation_id = uuid.UUID(conversation_id)
    msg2.user_id = uuid.UUID(user_id)
    msg2.content = "AI response"
    msg2.type = MessageType.AI
    msg2.created_at = datetime.now(timezone.utc)

    # Configure mock to return messages
    mock_message_repository.get_messages_by_conversation_id.return_value = [msg1, msg2]

    # Call the service method
    result = await message_service.get_conversation_history(
        conversation_id=conversation_id,
        user_id=user_id,
    )

    # Verify the result
    assert isinstance(result, list)
    assert len(result) == 2
    assert result[0].content == "User message"
    assert result[0].type == MessageType.USER
    assert result[1].content == "AI response"
    assert result[1].type == MessageType.AI
