"""
Background task for token counting and conversation compaction.
Runs outside of request context — uses its own DB session.
Project StakeHolder
"""

import logging

from src.database import SessionLocal
from src.repository.summary_repository import SummaryRepository
from src.repository.message_repository import MessageRepository
from src.service.history_compactor_service import HistoryCompactorService
from src.service.summary_service import SummaryService
from src.service.message_service import MessageService
from src.dependencies.services import get_history_compactor_service


logger = logging.getLogger("wide_event")


def _get_compactor() -> HistoryCompactorService:
    """Reuse the singleton compactor from the DI layer."""
    return get_history_compactor_service()


async def post_message_hook(
    conversation_id: str,
    *,
    correlation_id: str | None = None,
) -> None:
    """
    Background task fired after every request.
    Only needs conversation_id — gathers everything else itself.

    1. Get or create summary row for this conversation.
    2. Fetch messages WHERE created_at > window_end (or all if no window yet).
    3. Batch estimate tokens for those messages.
    4. Update window_end = last message's created_at.
    5. If running token_count >= 100k, run compaction.
    """
    async with SessionLocal() as session:
        summary_repo = SummaryRepository(session)
        message_repo = MessageRepository(session)
        message_service = MessageService(message_repository=message_repo)
        summary_service = SummaryService(
            summary_repository=summary_repo,
            message_service=message_service,
            history_compactor_service=_get_compactor(),
        )

        try:
            await summary_service.process_conversation(conversation_id)
        except Exception as e:
            logger.error(
                {
                    "event": "compaction_task_failed",
                    "conversation_id": conversation_id,
                    "correlation_id": correlation_id,
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                }
            )
