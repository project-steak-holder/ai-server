"""
Tests for the background compaction task.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from src.tasks.compaction_task import post_message_hook, TOKEN_THRESHOLD


@pytest.fixture
def mock_session():
    """Create a mock async session context manager."""
    session = AsyncMock()
    return session


@pytest.fixture
def mock_summary_repo():
    repo = MagicMock()
    repo.get_conversation_summary = AsyncMock(return_value=None)
    repo.update_summary = AsyncMock(return_value=None)
    return repo


@pytest.fixture
def mock_message_repo():
    repo = MagicMock()
    repo.get_messages_after = AsyncMock(return_value=[])
    repo.get_all_messages_by_conversation = AsyncMock(return_value=[])
    return repo


def _make_mock_message(content: str, created_at: datetime | None = None):
    import uuid

    msg = MagicMock()
    msg.content = content
    msg.created_at = created_at or datetime.now(timezone.utc)
    msg.id = uuid.uuid4()
    msg.conversation_id = uuid.uuid4()
    msg.type = "user"
    msg.role = "user"
    return msg


@pytest.mark.anyio
async def test_post_message_hook_first_pass_creates_summary(
    mock_summary_repo, mock_message_repo
):
    """First pass with no summary row creates one with initial window."""
    t1 = datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc)
    t2 = datetime(2026, 1, 1, 0, 5, tzinfo=timezone.utc)
    messages = [_make_mock_message("hello", t1), _make_mock_message("world", t2)]
    mock_message_repo.get_all_messages_by_conversation.return_value = messages
    mock_summary_repo.get_conversation_summary.return_value = None

    with (
        patch("src.tasks.compaction_task.SessionLocal") as mock_session_local,
        patch(
            "src.tasks.compaction_task.SummaryRepository",
            return_value=mock_summary_repo,
        ),
        patch(
            "src.tasks.compaction_task.MessageRepository",
            return_value=mock_message_repo,
        ),
    ):
        mock_session_local.return_value.__aenter__ = AsyncMock(return_value=AsyncMock())
        mock_session_local.return_value.__aexit__ = AsyncMock(return_value=False)

        await post_message_hook("conv-1")

    mock_summary_repo.update_summary.assert_called_once_with(
        conversation_id="conv-1",
        content=None,
        token_count=2,  # "hello" = 1 token, "world" = 1 token
        window_start=t1,
        window_end=t2,
    )


@pytest.mark.anyio
async def test_post_message_hook_below_threshold_updates_window(
    mock_summary_repo, mock_message_repo
):
    """Token count below threshold just updates window_end and token_count."""
    t_existing = datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc)
    t_new = datetime(2026, 1, 1, 0, 10, tzinfo=timezone.utc)

    existing_summary = MagicMock()
    existing_summary.content = None
    existing_summary.token_count = 100
    existing_summary.window_start = t_existing
    existing_summary.window_end = t_existing
    mock_summary_repo.get_conversation_summary.return_value = existing_summary

    messages = [_make_mock_message("short msg", t_new)]
    mock_message_repo.get_messages_after.return_value = messages

    with (
        patch("src.tasks.compaction_task.SessionLocal") as mock_session_local,
        patch(
            "src.tasks.compaction_task.SummaryRepository",
            return_value=mock_summary_repo,
        ),
        patch(
            "src.tasks.compaction_task.MessageRepository",
            return_value=mock_message_repo,
        ),
    ):
        mock_session_local.return_value.__aenter__ = AsyncMock(return_value=AsyncMock())
        mock_session_local.return_value.__aexit__ = AsyncMock(return_value=False)

        await post_message_hook("conv-1")

    mock_summary_repo.update_summary.assert_called_once_with(
        conversation_id="conv-1",
        content=None,
        token_count=102,  # 100 + len("short msg")//4 = 100 + 2
        window_start=t_existing,
        window_end=t_new,
    )


@pytest.mark.anyio
async def test_post_message_hook_above_threshold_triggers_compaction(
    mock_summary_repo, mock_message_repo
):
    """Token count crossing threshold triggers compaction and resets count."""
    t_start = datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc)
    t_end = datetime(2026, 1, 1, 0, 5, tzinfo=timezone.utc)
    t_new = datetime(2026, 1, 1, 0, 10, tzinfo=timezone.utc)

    existing_summary = MagicMock()
    existing_summary.content = None
    existing_summary.token_count = TOKEN_THRESHOLD - 1
    existing_summary.window_start = t_start
    existing_summary.window_end = t_end
    mock_summary_repo.get_conversation_summary.return_value = existing_summary

    # New message pushes over threshold
    new_msg = _make_mock_message("a" * 40, t_new)  # 10 tokens
    mock_message_repo.get_messages_after.return_value = [new_msg]

    mock_compactor = MagicMock()
    mock_compactor.summarize = AsyncMock(return_value="Compacted summary")

    with (
        patch("src.tasks.compaction_task.SessionLocal") as mock_session_local,
        patch(
            "src.tasks.compaction_task.SummaryRepository",
            return_value=mock_summary_repo,
        ),
        patch(
            "src.tasks.compaction_task.MessageRepository",
            return_value=mock_message_repo,
        ),
        patch("src.tasks.compaction_task._get_compactor", return_value=mock_compactor),
    ):
        mock_session_local.return_value.__aenter__ = AsyncMock(return_value=AsyncMock())
        mock_session_local.return_value.__aexit__ = AsyncMock(return_value=False)

        await post_message_hook("conv-1")

    mock_compactor.summarize.assert_called_once()
    mock_summary_repo.update_summary.assert_called_once_with(
        conversation_id="conv-1",
        content="Compacted summary",
        token_count=0,
        window_start=t_new,
        window_end=t_new,
    )


@pytest.mark.anyio
async def test_post_message_hook_prepends_existing_summary(
    mock_summary_repo, mock_message_repo
):
    """Compaction prepends existing summary content."""
    t_start = datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc)
    t_end = datetime(2026, 1, 1, 0, 5, tzinfo=timezone.utc)
    t_new = datetime(2026, 1, 1, 0, 10, tzinfo=timezone.utc)

    existing_summary = MagicMock()
    existing_summary.content = "Old summary"
    existing_summary.token_count = TOKEN_THRESHOLD
    existing_summary.window_start = t_start
    existing_summary.window_end = t_end
    mock_summary_repo.get_conversation_summary.return_value = existing_summary

    new_msg = _make_mock_message("a" * 40, t_new)
    mock_message_repo.get_messages_after.return_value = [new_msg]

    mock_compactor = MagicMock()
    mock_compactor.summarize = AsyncMock(return_value="New summary")

    with (
        patch("src.tasks.compaction_task.SessionLocal") as mock_session_local,
        patch(
            "src.tasks.compaction_task.SummaryRepository",
            return_value=mock_summary_repo,
        ),
        patch(
            "src.tasks.compaction_task.MessageRepository",
            return_value=mock_message_repo,
        ),
        patch("src.tasks.compaction_task._get_compactor", return_value=mock_compactor),
    ):
        mock_session_local.return_value.__aenter__ = AsyncMock(return_value=AsyncMock())
        mock_session_local.return_value.__aexit__ = AsyncMock(return_value=False)

        await post_message_hook("conv-1")

    call_kwargs = mock_summary_repo.update_summary.call_args.kwargs
    assert call_kwargs["content"] == "Old summary\n\nNew summary"


@pytest.mark.anyio
async def test_post_message_hook_no_new_messages_is_noop(
    mock_summary_repo, mock_message_repo
):
    """No new messages means no work done."""
    existing_summary = MagicMock()
    existing_summary.window_end = datetime(2026, 1, 1, tzinfo=timezone.utc)
    mock_summary_repo.get_conversation_summary.return_value = existing_summary
    mock_message_repo.get_messages_after.return_value = []

    with (
        patch("src.tasks.compaction_task.SessionLocal") as mock_session_local,
        patch(
            "src.tasks.compaction_task.SummaryRepository",
            return_value=mock_summary_repo,
        ),
        patch(
            "src.tasks.compaction_task.MessageRepository",
            return_value=mock_message_repo,
        ),
    ):
        mock_session_local.return_value.__aenter__ = AsyncMock(return_value=AsyncMock())
        mock_session_local.return_value.__aexit__ = AsyncMock(return_value=False)

        await post_message_hook("conv-1")

    mock_summary_repo.update_summary.assert_not_called()
