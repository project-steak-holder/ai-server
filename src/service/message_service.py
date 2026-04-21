"""
Message persistence service
Project SteakHolder
"""

from src.middlewares.events import wide_event
from src.repository.message_repository import MessageRepository
from src.models.message import Message
from src.schemas.message_model import MessageType


class MessageService:
    """Service for handling messages."""

    def __init__(self, message_repository: MessageRepository) -> None:
        self.message_repository = message_repository

    @wide_event("save_user_message")
    async def save_user_message(
        self, conversation_id: str, user_id: str, content: str
    ) -> Message:
        """Save a user message to the database."""
        return await self.message_repository.save_message(
            conversation_id=conversation_id,
            user_id=user_id,
            content=content,
            type=MessageType.USER,
        )

    @wide_event("save_ai_message")
    async def save_ai_message(
        self, conversation_id: str, user_id: str, content: str
    ) -> Message:
        """Save an AI message to the database."""
        return await self.message_repository.save_message(
            conversation_id=conversation_id,
            user_id=user_id,
            content=content,
            type=MessageType.AI,
        )

    @wide_event("get_conversation_history")
    async def get_conversation_history(
        self, conversation_id: str, user_id: str
    ) -> list[Message]:
        """Retrieve the message history for a given conversation."""
        return await self.message_repository.get_messages_by_conversation_id(
            conversation_id=conversation_id,
            user_id=user_id,
        )

    async def get_all_messages_by_conversation(
        self, conversation_id: str
    ) -> list[Message]:
        """Retrieve all messages for a conversation (background/internal use)."""
        return await self.message_repository.get_all_messages_by_conversation(
            conversation_id=conversation_id,
        )

    async def get_messages_after(self, conversation_id: str, after) -> list[Message]:
        """Retrieve messages created after a timestamp (background/internal use)."""
        return await self.message_repository.get_messages_after(
            conversation_id=conversation_id,
            after=after,
        )
