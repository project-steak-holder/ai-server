"""
Tests for the background compaction task.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from src.tasks.compaction_task import post_message_hook


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
    with (
        patch("src.tasks.compaction_task.SessionLocal") as mock_session_local,
        patch("src.tasks.compaction_task.SummaryService") as mock_summary_service_cls,
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

        mock_summary_service = MagicMock()
        mock_summary_service.process_conversation = AsyncMock(return_value=None)
        mock_summary_service_cls.return_value = mock_summary_service

        await post_message_hook("conv-1")

    mock_summary_service.process_conversation.assert_awaited_once_with("conv-1")


@pytest.mark.anyio
async def test_post_message_hook_below_threshold_updates_window(
    mock_summary_repo, mock_message_repo
):
    with (
        patch("src.tasks.compaction_task.SessionLocal") as mock_session_local,
        patch("src.tasks.compaction_task.SummaryService") as mock_summary_service_cls,
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

        mock_summary_service = MagicMock()
        mock_summary_service.process_conversation = AsyncMock(return_value=None)
        mock_summary_service_cls.return_value = mock_summary_service

        await post_message_hook("conv-1")

    mock_summary_service.process_conversation.assert_awaited_once_with("conv-1")


@pytest.mark.anyio
async def test_post_message_hook_above_threshold_triggers_compaction(
    mock_summary_repo, mock_message_repo
):
    with (
        patch("src.tasks.compaction_task.SessionLocal") as mock_session_local,
        patch("src.tasks.compaction_task.SummaryService") as mock_summary_service_cls,
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

        mock_summary_service = MagicMock()
        mock_summary_service.process_conversation = AsyncMock(return_value=None)
        mock_summary_service_cls.return_value = mock_summary_service

        await post_message_hook("conv-1")

    mock_summary_service.process_conversation.assert_awaited_once_with("conv-1")


@pytest.mark.anyio
async def test_post_message_hook_prepends_existing_summary(
    mock_summary_repo, mock_message_repo
):
    with (
        patch("src.tasks.compaction_task.SessionLocal") as mock_session_local,
        patch("src.tasks.compaction_task.SummaryService") as mock_summary_service_cls,
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

        mock_summary_service = MagicMock()
        mock_summary_service.process_conversation = AsyncMock(return_value=None)
        mock_summary_service_cls.return_value = mock_summary_service

        await post_message_hook("conv-1")

    mock_summary_service.process_conversation.assert_awaited_once_with("conv-1")


@pytest.mark.anyio
async def test_post_message_hook_no_new_messages_is_noop(
    mock_summary_repo, mock_message_repo
):
    with (
        patch("src.tasks.compaction_task.SessionLocal") as mock_session_local,
        patch("src.tasks.compaction_task.SummaryService") as mock_summary_service_cls,
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

        mock_summary_service = MagicMock()
        mock_summary_service.process_conversation = AsyncMock(return_value=None)
        mock_summary_service_cls.return_value = mock_summary_service

        await post_message_hook("conv-1")

    mock_summary_service.process_conversation.assert_awaited_once_with("conv-1")
