"""
Test class for HistoryCompactorService.
"""

import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock
from pydantic_ai import ModelRequest, ModelResponse, TextPart

from src.schemas.message_model import Message, MessageType
from src.service.history_compactor_service import HistoryCompactorService


@pytest.fixture(autouse=True)
def mock_summarize_agent_run_with_five_messages(monkeypatch):
    """Fixture to mock summarize_agent.run on HistoryCompactorService instance without requiring real provider."""
    monkeypatch.setattr(HistoryCompactorService, "__init__", lambda self: None)

    def setup_agent(self):
        self.summarize_agent = MagicMock()
        self.summarize_agent.run = AsyncMock()
        mock_result = MagicMock()
        mock_result.new_messages.return_value = [
            ModelResponse(parts=[TextPart(content="Summary of old messages")])
        ]
        self.summarize_agent.run.return_value = mock_result

    HistoryCompactorService.setup_agent = setup_agent
    yield


@pytest.mark.anyio
async def test_summarize_old_messages_no_needed_summarization():
    """Test summarize_old_messages returns input unchanged when <= 10 messages."""
    messages = [
        Message(
            id=uuid.uuid4(),
            conversation_id=uuid.uuid4(),
            content=f"Message {i}",
            type=MessageType.USER if i % 2 == 0 else MessageType.AI,
        )
        for i in range(5)
    ]
    svc = HistoryCompactorService()
    svc.setup_agent()
    result = await svc.summarize_old_messages(messages)
    assert len(result) == 5
    assert all(isinstance(msg, (ModelRequest, ModelResponse)) for msg in result)


@pytest.mark.anyio
async def test_summarize_old_messages_with_summarization():
    """Test summarize_old_messages summarizes old messages and keeps recent ones."""
    messages = [
        Message(
            id=uuid.uuid4(),
            conversation_id=uuid.uuid4(),
            content=f"Message {i}",
            type=MessageType.USER if i % 2 == 0 else MessageType.AI,
        )
        for i in range(15)
    ]
    svc = HistoryCompactorService()
    svc.setup_agent()
    result = await svc.summarize_old_messages(messages)
    assert len(result) == 11  # summary + 10 recent
    assert all(isinstance(msg, (ModelRequest, ModelResponse)) for msg in result)
