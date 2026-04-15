"""
Test class for HistoryCompactorService.
"""

import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock
from pydantic_ai import ModelRequest, ModelResponse

from src.schemas.message_model import Message, MessageType
from src.service.history_compactor_service import HistoryCompactorService


@pytest.fixture(autouse=True)
def mock_compactor_init(monkeypatch):
    """Mock __init__ to avoid requiring real API key."""
    monkeypatch.setattr(HistoryCompactorService, "__init__", lambda self: None)

    def setup_agent(self):
        self.summarize_agent = MagicMock()
        self.summarize_agent.run = AsyncMock()
        mock_result = MagicMock()
        mock_result.output = "Summary of old messages"
        self.summarize_agent.run.return_value = mock_result

    HistoryCompactorService.setup_agent = setup_agent  # type: ignore[attr-defined]
    yield


def _make_messages(count: int) -> list[Message]:
    """Helper to create a list of test messages."""
    conversation_id = uuid.uuid4()
    return [
        Message(
            id=uuid.uuid4(),
            conversation_id=conversation_id,
            content=f"Message {i}",
            type=MessageType.USER if i % 2 == 0 else MessageType.AI,
        )
        for i in range(count)
    ]


class TestEstimateTokens:
    """Tests for the static estimate_tokens method."""

    def test_estimate_tokens_basic(self):
        assert HistoryCompactorService.estimate_tokens("abcd") == 1

    def test_estimate_tokens_empty(self):
        assert HistoryCompactorService.estimate_tokens("") == 0

    def test_estimate_tokens_long_content(self):
        content = "a" * 400
        assert HistoryCompactorService.estimate_tokens(content) == 100

    def test_estimate_tokens_short_content(self):
        assert HistoryCompactorService.estimate_tokens("hi") == 0


class TestSummarize:
    """Tests for the async summarize method."""

    @pytest.mark.anyio
    async def test_summarize_returns_summary_text(self):
        svc = HistoryCompactorService()
        svc.setup_agent()  # type: ignore[attr-defined]
        messages = _make_messages(5)
        result = await svc.summarize(messages)
        assert result == "Summary of old messages"
        svc.summarize_agent.run.assert_called_once()  # type: ignore[attr-defined]

    @pytest.mark.anyio
    async def test_summarize_passes_converted_messages(self):
        svc = HistoryCompactorService()
        svc.setup_agent()  # type: ignore[attr-defined]
        messages = _make_messages(3)
        await svc.summarize(messages)
        call_kwargs = svc.summarize_agent.run.call_args  # type: ignore[attr-defined]
        history = call_kwargs.kwargs["message_history"]
        assert len(history) == 3
        assert all(isinstance(m, (ModelRequest, ModelResponse)) for m in history)
