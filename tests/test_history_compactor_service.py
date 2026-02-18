"""
Test class for HistoryCompactorService.
"""

import uuid
import pytest
from unittest.mock import AsyncMock

from src.schemas.message_model import Message, RoleEnum
from src.service.history_compactor_service import HistoryCompactorService


@pytest.fixture(autouse=True)
def mock_summarize_agent_run(monkeypatch):
    """Fixture to mock summarize_agent.run for all tests in this module."""
    from src.service import history_compactor_service
    mock_run = AsyncMock()
    summary_dict = {"role": "ai", "content": "Summary of earlier messages"}
    # Make new_messages a regular method, not an async one
    mock_run.return_value.new_messages = lambda: [summary_dict]
    monkeypatch.setattr(history_compactor_service.summarize_agent, "run", mock_run)
    return mock_run


def test_convert_to_dictlist():
    """Test conversion of MessageModel list to dict list."""
    messages = [
        Message(
            id=uuid.uuid4(),
            conversation_id=uuid.uuid4(),
            content="Hello!",
            role=RoleEnum.user
        ),
        Message(
            id=uuid.uuid4(),
            conversation_id=uuid.uuid4(),
            content="Hi, how can I help?",
            role=RoleEnum.ai
        ),
    ]
    dict_list = HistoryCompactorService.convert_to_dictlist(messages)
    assert isinstance(dict_list, list)
    assert all(isinstance(msg, dict) for msg in dict_list)
    assert dict_list[0]["role"] == "user"
    assert dict_list[0]["content"] == "Hello!"
    assert dict_list[1]["role"] == "ai"
    assert dict_list[1]["content"] == "Hi, how can I help?"



@pytest.mark.anyio
async def test_summarize_old_messages_no_needed_summarization():
    """Test summarize_old_messages returns input unchanged when <= 10 messages."""
    messages = [
        Message(
            id=uuid.uuid4(),
            conversation_id=uuid.uuid4(),
            content=f"Message {i}",
            role=RoleEnum.user if i % 2 == 0 else RoleEnum.ai
        )
        for i in range(5)
    ]
    result = await HistoryCompactorService.summarize_old_messages(messages)
    assert len(result) == 5
    assert all(isinstance(msg, dict) for msg in result)
    for i, msg in enumerate(result):
        assert msg["content"] == f"Message {i}"
        assert msg["role"] in ("user", "ai")



@pytest.mark.anyio
async def test_summarize_old_messages_with_summarization():
    """Test summarize_old_messages summarizes old messages and keeps recent ones."""
    messages = [
        Message(
            id=uuid.uuid4(),
            conversation_id=uuid.uuid4(),
            content=f"Message {i}",
            role=RoleEnum.user if i % 2 == 0 else RoleEnum.ai
        )
        for i in range(15)
    ]
    result = await HistoryCompactorService.summarize_old_messages(messages)
    # Should return a summary (as dict) plus the 10 most recent messages
    assert len(result) == 11  # 1 summary + 10 recent
    assert result[0]["role"] == "ai"
    assert result[0]["content"] == "Summary of earlier messages"
    for msg in result[1:]:  # Recent messages should be dicts
        assert isinstance(msg, dict)
        assert msg["content"] in [f"Message {i}" for i in range(5, 15)]
        assert msg["role"] in ("user", "ai")
