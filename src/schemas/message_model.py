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
from typing import Optional
from pydantic import BaseModel, ConfigDict
from enum import Enum

class RoleEnum(str, Enum):
    """Defines role of message sender"""
    user = "user"
    ai = "ai"


class Message(BaseModel):
    """Pydantic model for individual messages in a conversation."""
    model_config = ConfigDict(
        # Allow reading from ORM objects (needed for SQLAlchemy)
        from_attributes=True,
    )

    # more fields available from orm message model if needed
    id: Optional[uuid.UUID]
    conversation_id: uuid.UUID
    content: str
    role: RoleEnum
