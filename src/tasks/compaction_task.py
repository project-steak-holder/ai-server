"""
Background task for token counting and conversation compaction.
Runs outside of request context — uses its own DB session.
Project StakeHolder
"""

from src.database import SessionLocal
from src.repository.summary_repository import SummaryRepository
from src.repository.message_repository import MessageRepository
from src.service.history_compactor_service import HistoryCompactorService
from src.schemas.message_model import Message

TOKEN_THRESHOLD = 100_000


def _get_compactor() -> HistoryCompactorService:
    """Reuse the singleton compactor from the DI layer."""
    from src.dependencies.services import get_history_compactor_service

    return get_history_compactor_service()


async def post_message_hook(conversation_id: str) -> None:
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

        summary = await summary_repo.get_conversation_summary(conversation_id)

        # Fetch unprocessed messages
        if summary and summary.window_end:
            new_messages = await message_repo.get_messages_after(
                conversation_id, summary.window_end
            )
        else:
            new_messages = await message_repo.get_all_messages_by_conversation(
                conversation_id
            )

        if not new_messages:
            return

        # Batch estimate tokens
        new_tokens: int = 0
        for msg in new_messages:
            new_tokens += HistoryCompactorService.estimate_tokens(msg.content)  # type: ignore[arg-type]

        first_msg_time = new_messages[0].created_at
        last_msg_time = new_messages[-1].created_at

        if summary is None:
            # First pass — create summary row with initial window
            await summary_repo.update_summary(
                conversation_id=conversation_id,
                content=None,
                token_count=new_tokens,
                window_start=first_msg_time,
                window_end=last_msg_time,
            )
            return

        updated_token_count = summary.token_count + new_tokens

        if updated_token_count >= TOKEN_THRESHOLD:
            # Compaction needed — summarize unprocessed messages
            compactor = _get_compactor()

            validated = [
                Message.model_validate(m, from_attributes=True) for m in new_messages
            ]

            summary_text = await compactor.summarize(validated)

            # Prepend existing summary if present
            if summary.content:
                summary_text = summary.content + "\n\n" + summary_text

            await summary_repo.update_summary(
                conversation_id=conversation_id,
                content=summary_text,
                token_count=0,
                window_start=first_msg_time,
                window_end=last_msg_time,
            )
        else:
            # No compaction — just update window and counts
            await summary_repo.update_summary(
                conversation_id=conversation_id,
                content=summary.content,
                token_count=updated_token_count,
                window_start=summary.window_start,
                window_end=last_msg_time,
            )
