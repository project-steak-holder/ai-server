from src.models.summary import Summary
from src.repository.base import BaseCRUDRepository


class SummaryRepository(BaseCRUDRepository):
    async def get_conversation_summary(self, conversation_id):
        """Get the summary for a given conversation ID."""
        return await self.get_by_field("conversation_id", conversation_id)

    async def update_summary(
        self, conversation_id, content, token_count, window_start, window_end
    ):
        """Update or create the summary for a given conversation ID."""
        summary = await self.get_conversation_summary(conversation_id)
        if summary:
            summary.content = content
            summary.token_count = token_count
            summary.window_start = window_start
            summary.window_end = window_end
        else:
            summary = Summary(
                conversation_id=conversation_id,
                content=content,
                token_count=token_count,
                window_start=window_start,
                window_end=window_end,
            )
        return await self.update(summary)

    pass
