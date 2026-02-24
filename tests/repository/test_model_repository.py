"""Unit tests for MessageRepository."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.repository.model_repository import MessageRepository
from src.schemas.message_model import MessageType


class RepoResultScalarsAll:
    def __init__(self, values):
        self._values = values

    def scalars(self):
        return self

    def all(self):
        return self._values


@pytest.mark.anyio
async def test_message_repository_methods():
    session = AsyncMock()
    repo = MessageRepository(session)

    created = MagicMock()
    with patch.object(repo, "create", AsyncMock(return_value=created)) as mock_create:
        result = await repo.save_message("c1", "u1", "hello", MessageType.USER)

    assert result is created
    message_arg = mock_create.await_args.args[0]
    assert message_arg.content == "hello"
    assert message_arg.type == MessageType.USER

    session.execute.return_value = RepoResultScalarsAll(["m1", "m2"])
    messages = await repo.get_messages_by_conversation_id("c1", "u1")
    assert messages == ["m1", "m2"]

    with patch.object(repo, "delete", AsyncMock()) as mock_delete:
        await repo.delete_message("msg")
        mock_delete.assert_awaited_once_with("msg")
