"""Unit tests for MessageRepository."""

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
    message_arg = mock_create.await_args.args[0]
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


# Test delete_message
@pytest.mark.anyio
async def test_delete_message():
    session = AsyncMock()
    repo = MessageRepository(session)
    with patch.object(repo, "delete", AsyncMock()) as mock_delete:
        await repo.delete_message("msg")
        mock_delete.assert_awaited_once_with("msg")
