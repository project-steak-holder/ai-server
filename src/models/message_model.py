"""
Project Steak-Holder
Message model

individual message objects retrieved from DB will be saved as Message models

contains:
- messageID
- conversationID
- content
"""
import uuid
from typing import Optional
from pydantic import BaseModel

class Message(BaseModel):
    # more fields available from orm message model if needed
    id: Optional[uuid.UUID]
    conversation_id: uuid.UUID
    content: str