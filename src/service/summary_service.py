from datetime import datetime

from src.repository.summary_repository import SummaryRepository
from src.service.history_compactor_service import HistoryCompactorService
from src.service.message_service import MessageService
from src.schemas.message_model import Message


TOKEN_THRESHOLD = 100_000


class SummaryService:
    def __init__(
        self,
        summary_repository: SummaryRepository,
        *,
        message_service: MessageService | None = None,
        history_compactor_service: HistoryCompactorService | None = None,
    ) -> None:
        self.summary_repository = summary_repository
        self.message_service = message_service
        self.history_compactor_service = history_compactor_service

    async def get_conversation_summary(self, conversation_id: str):
        return await self.summary_repository.get_conversation_summary(conversation_id)

    async def update_summary(
        self,
        conversation_id: str,
        content: str | None,
        token_count: int,
        window_start: datetime | None,
        window_end: datetime | None,
    ):
        return await self.summary_repository.update_summary(
            conversation_id=conversation_id,
            content=content,
            token_count=token_count,
            window_start=window_start,
            window_end=window_end,
        )

    async def process_conversation(self, conversation_id: str) -> None:
        if self.message_service is None:
            raise ValueError(
                "SummaryService requires message_service for process_conversation"
            )
        if self.history_compactor_service is None:
            raise ValueError(
                "SummaryService requires history_compactor_service for process_conversation"
            )

        summary = await self.get_conversation_summary(conversation_id)

        if summary and summary.window_end:
            new_messages = await self.message_service.get_messages_after(
                conversation_id,
                summary.window_end,
            )
        else:
            new_messages = await self.message_service.get_all_messages_by_conversation(
                conversation_id,
            )

        if not new_messages:
            return

        new_tokens: int = 0
        for msg in new_messages:
            new_tokens += HistoryCompactorService.estimate_tokens(msg.content)  # type: ignore[arg-type]

        first_msg_time = new_messages[0].created_at
        last_msg_time = new_messages[-1].created_at

        if summary is None or summary.window_end is None:
            await self.update_summary(
                conversation_id=conversation_id,
                content=None,
                token_count=new_tokens,
                window_start=first_msg_time,
                window_end=last_msg_time,
            )
            return

        updated_token_count = summary.token_count + new_tokens

        if updated_token_count >= TOKEN_THRESHOLD:
            validated = [
                Message.model_validate(m, from_attributes=True) for m in new_messages
            ]
            summary_text = await self.history_compactor_service.summarize(
                validated,
                previous_summary=summary.content,
            )

            await self.update_summary(
                conversation_id=conversation_id,
                content=summary_text,
                token_count=0,
                window_start=last_msg_time,
                window_end=last_msg_time,
            )
        else:
            await self.update_summary(
                conversation_id=conversation_id,
                content=summary.content,
                token_count=updated_token_count,
                window_start=summary.window_start,
                window_end=last_msg_time,
            )
