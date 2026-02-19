"""
Test class for HistoryCompactorService.
"""

import uuid
import pytest
from unittest.mock import AsyncMock, patch
from pydantic_ai import ModelRequest, ModelResponse, TextPart

from src.schemas.message_model import Message, RoleEnum
from src.service.history_compactor_service import HistoryCompactorService


@pytest.fixture(autouse=True)
def mock_summarize_agent_run():
    with patch("src.service.history_compactor_service.summarize_agent.run", new_callable=AsyncMock) as mock_run:
        mock_run.return_value = [ModelResponse(parts=[TextPart(content="Summary")])]
        yield


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
    assert all(isinstance(msg, (ModelRequest, ModelResponse)) for msg in result)

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
    assert len(result) == 11  # summary + 10 recent
    assert all(isinstance(msg, (ModelRequest, ModelResponse)) for msg in result)
