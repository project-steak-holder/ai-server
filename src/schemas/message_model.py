"""
Project Steak-Holder
Message model

individual message objects retrieved from DB will be saved as Message models

contains:
- messageID
- conversationID
- content
- role (user or ai)
"""

import uuid
from pydantic import BaseModel, ConfigDict, Field
from enum import Enum


class MessageType(Enum):
    USER = "user"
    AI = "ai"


class Message(BaseModel):
    """Pydantic model for individual messages in a conversation."""

    model_config = ConfigDict(
        # Allow reading from ORM objects (needed for SQLAlchemy)
        from_attributes=True,
        populate_by_name=True,  # Allow using alias 'type' in constructors
    )

    # more fields available from orm message model if needed
    id: uuid.UUID
    conversation_id: uuid.UUID
    content: str
    # alias between role and type
    # to match both DB model and agent framework expectations
    role: MessageType = Field(alias="type")
