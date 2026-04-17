"""
Tests for SummaryService.process_conversation — covers the three branches
of the sliding-window compaction logic plus the no-new-messages early exit.
"""

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.schemas.message_model import MessageType
from src.service.summary_service import SummaryService, TOKEN_THRESHOLD


def _mock_message(content: str, created_at: datetime):
    msg = MagicMock()
    msg.id = uuid.uuid4()
    msg.conversation_id = uuid.uuid4()
    msg.content = content
    msg.created_at = created_at
    msg.type = MessageType.USER
    msg.role = MessageType.USER
    return msg


def _mock_summary(
    *,
    content: str | None,
    token_count: int,
    window_start: datetime,
    window_end: datetime,
):
    summary = MagicMock()
    summary.content = content
    summary.token_count = token_count
    summary.window_start = window_start
    summary.window_end = window_end
    return summary


@pytest.fixture
def mock_summary_repo():
    repo = MagicMock()
    repo.get_conversation_summary = AsyncMock(return_value=None)
    repo.update_summary = AsyncMock(return_value=None)
    return repo


@pytest.fixture
def mock_message_service():
    svc = MagicMock()
    svc.get_messages_after = AsyncMock(return_value=[])
    svc.get_all_messages_by_conversation = AsyncMock(return_value=[])
    return svc


@pytest.fixture
def mock_compactor():
    svc = MagicMock()
    svc.summarize = AsyncMock(return_value="unified summary text")
    return svc


@pytest.fixture
def service(mock_summary_repo, mock_message_service, mock_compactor):
    return SummaryService(
        summary_repository=mock_summary_repo,
        message_service=mock_message_service,
        history_compactor_service=mock_compactor,
    )


class TestProcessConversation:
    @pytest.mark.anyio
    async def test_no_new_messages_is_noop(
        self, service, mock_summary_repo, mock_message_service
    ):
        mock_summary_repo.get_conversation_summary.return_value = None
        mock_message_service.get_all_messages_by_conversation.return_value = []

        await service.process_conversation("conv-1")

        mock_summary_repo.update_summary.assert_not_called()

    @pytest.mark.anyio
    async def test_first_pass_creates_summary_row(
        self, service, mock_summary_repo, mock_message_service, mock_compactor
    ):
        """No existing summary → initializer branch: content=None, token_count=new_tokens,
        window spans first to last new message. Compactor NOT called."""
        t0 = datetime(2026, 1, 1, tzinfo=timezone.utc)
        t1 = t0 + timedelta(seconds=1)
        messages = [_mock_message("hi", t0), _mock_message("there", t1)]

        mock_summary_repo.get_conversation_summary.return_value = None
        mock_message_service.get_all_messages_by_conversation.return_value = messages

        await service.process_conversation("conv-1")

        mock_compactor.summarize.assert_not_called()
        mock_summary_repo.update_summary.assert_awaited_once()
        call_kwargs = mock_summary_repo.update_summary.await_args.kwargs
        assert call_kwargs["content"] is None
        assert call_kwargs["window_start"] == t0
        assert call_kwargs["window_end"] == t1
        # token count = sum of len(content)//4 for each message
        assert call_kwargs["token_count"] == (len("hi") // 4) + (len("there") // 4)

    @pytest.mark.anyio
    async def test_below_threshold_extends_window_end_preserves_start(
        self, service, mock_summary_repo, mock_message_service, mock_compactor
    ):
        """Existing summary + new tokens stay under threshold → preserve window_start,
        slide window_end, accumulate token_count, keep content unchanged.

        Scaled relative to TOKEN_THRESHOLD so this test is robust to threshold
        changes (1k for dev, 100k for prod)."""
        prior_tokens = TOKEN_THRESHOLD // 2
        # Tiny new message: 4 chars = 1 token. Prior + new = THRESHOLD//2 + 1,
        # strictly below threshold for any THRESHOLD >= 3.
        new_content = "abcd"
        expected_new_tokens = len(new_content) // 4

        prev_start = datetime(2026, 1, 1, tzinfo=timezone.utc)
        prev_end = datetime(2026, 1, 1, 0, 0, 5, tzinfo=timezone.utc)
        summary = _mock_summary(
            content="prior summary",
            token_count=prior_tokens,
            window_start=prev_start,
            window_end=prev_end,
        )
        mock_summary_repo.get_conversation_summary.return_value = summary

        t_new = prev_end + timedelta(seconds=10)
        mock_message_service.get_messages_after.return_value = [
            _mock_message(new_content, t_new)
        ]

        await service.process_conversation("conv-1")

        # Sanity: we are in fact below threshold
        assert prior_tokens + expected_new_tokens < TOKEN_THRESHOLD

        mock_compactor.summarize.assert_not_called()
        call_kwargs = mock_summary_repo.update_summary.await_args.kwargs
        assert call_kwargs["content"] == "prior summary"
        assert call_kwargs["window_start"] == prev_start  # preserved
        assert call_kwargs["window_end"] == t_new  # slid forward
        assert call_kwargs["token_count"] == prior_tokens + expected_new_tokens

    @pytest.mark.anyio
    async def test_threshold_triggers_compaction_and_collapses_window(
        self, service, mock_summary_repo, mock_message_service, mock_compactor
    ):
        """Crossing threshold → summarize is called with previous_summary, token_count
        resets to 0, and both window_start and window_end collapse to last_msg_time.

        Scaled relative to TOKEN_THRESHOLD so this test guarantees crossover for
        any threshold value (1k dev, 100k prod, etc.)."""
        prior_tokens = TOKEN_THRESHOLD // 2
        # Each message = THRESHOLD tokens (chars = tokens * 4). Two of them means
        # prior + new = THRESHOLD//2 + 2*THRESHOLD >= THRESHOLD for any THRESHOLD > 0.
        big_content = "x" * (TOKEN_THRESHOLD * 4)

        prev_start = datetime(2026, 1, 1, tzinfo=timezone.utc)
        prev_end = datetime(2026, 1, 1, 0, 0, 5, tzinfo=timezone.utc)
        summary = _mock_summary(
            content="prior summary content",
            token_count=prior_tokens,
            window_start=prev_start,
            window_end=prev_end,
        )
        mock_summary_repo.get_conversation_summary.return_value = summary

        t_first_new = prev_end + timedelta(seconds=10)
        t_last_new = prev_end + timedelta(seconds=20)
        messages = [
            _mock_message(big_content, t_first_new),
            _mock_message(big_content, t_last_new),
        ]
        mock_message_service.get_messages_after.return_value = messages

        # Sanity: we are in fact at/over threshold
        new_tokens = sum(len(m.content) // 4 for m in messages)
        assert prior_tokens + new_tokens >= TOKEN_THRESHOLD

        await service.process_conversation("conv-1")

        mock_compactor.summarize.assert_awaited_once()
        compactor_call = mock_compactor.summarize.await_args
        # previous_summary must be forwarded so the LLM can produce a unified rewrite
        assert compactor_call.kwargs["previous_summary"] == "prior summary content"

        update_kwargs = mock_summary_repo.update_summary.await_args.kwargs
        assert update_kwargs["content"] == "unified summary text"
        assert update_kwargs["token_count"] == 0
        # Sliding-window invariant: after compaction the uncompacted window is empty,
        # anchored at the last compacted message's timestamp.
        assert update_kwargs["window_start"] == t_last_new
        assert update_kwargs["window_end"] == t_last_new
