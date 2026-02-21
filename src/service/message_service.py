"""
Message persistence service
Project SteakHolder
"""

from src.repository.model_repository import MessageRepository
from src.models.message import Message
from src.schemas.message_model import MessageType


class MessageService:
    """Service for handling messages."""

    def __init__(self, message_repository: MessageRepository) -> None:
        self.message_repository = message_repository

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

    async def get_conversation_history(
        self, conversation_id: str, user_id: str
    ) -> list[Message]:
        """Retrieve the message history for a given conversation."""
        return await self.message_repository.get_messages_by_conversation_id(
            conversation_id=conversation_id,
            user_id=user_id,
        )
