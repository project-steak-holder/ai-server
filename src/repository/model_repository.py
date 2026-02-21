from sqlalchemy import select
from src.repository.base import BaseCRUDRepository
from src.models.message import Message
from src.schemas.message_model import MessageType


class MessageRepository(BaseCRUDRepository[Message]):
    """Repository for managing database operations related to messages."""

    async def save_message(
        self,
        conversation_id: str,
        user_id: str,
        content: str,
        type: MessageType,
    ) -> Message:
        """Create a new message record."""
        message = Message(
            conversation_id=conversation_id,
            user_id=user_id,
            content=content,
            type=type,
        )
        return await self.create(message)

    async def get_messages_by_conversation_id(
        self, conversation_id: str, user_id: str
    ) -> list[Message]:
        """Fetch all messages for a given conversation, ordered by creation time."""
        stmt = (
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .where(Message.user_id == user_id)
            .order_by(Message.created_at)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def delete_message(self, message: Message) -> None:
        """Delete a message record."""
        await self.delete(message)
