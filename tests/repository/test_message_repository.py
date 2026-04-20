"""Unit tests for MessageRepository."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.repository.message_repository import MessageRepository
from src.schemas.message_model import MessageType


class RepoResultScalarsAll:
    def __init__(self, values):
        self._values = values

    def scalars(self):
        return self

    def all(self):
        return self._values


# Test save_message
@pytest.mark.anyio
async def test_save_message():
    session = AsyncMock()
    repo = MessageRepository(session)
    created = MagicMock()
    with patch.object(repo, "create", AsyncMock(return_value=created)) as mock_create:
        result = await repo.save_message("c1", "u1", "hello", MessageType.USER)
    assert result is created
    # Safely extract the argument passed to mock_create
    if mock_create.await_args is not None:
        message_arg = mock_create.await_args.args[0]
    else:
        message_arg = mock_create.call_args.args[0]
    assert message_arg.content == "hello"
    assert message_arg.type == MessageType.USER


# Test get_messages_by_conversation_id
@pytest.mark.anyio
async def test_get_messages_by_conversation_id():
    session = AsyncMock()
    repo = MessageRepository(session)
    session.execute.return_value = RepoResultScalarsAll(["m1", "m2"])
    messages = await repo.get_messages_by_conversation_id("c1", "u1")
    assert messages == ["m1", "m2"]


# Test get_messages_after
@pytest.mark.anyio
async def test_get_messages_after():
    session = AsyncMock()
    repo = MessageRepository(session)
    session.execute.return_value = RepoResultScalarsAll(["m3", "m4"])
    after = datetime(2026, 1, 1, tzinfo=timezone.utc)
    messages = await repo.get_messages_after("c1", after)
    assert messages == ["m3", "m4"]


# Test delete_message
@pytest.mark.anyio
async def test_delete_message():
    session = AsyncMock()
    repo = MessageRepository(session)
    with patch.object(repo, "delete", AsyncMock()) as mock_delete:
        # Create a dummy Message object to pass to delete_message
        from src.models import Message

        dummy_message = Message(id="msg", content="", created_at=None, updated_at=None)
        await repo.delete_message(dummy_message)
        mock_delete.assert_awaited_once_with(dummy_message)
