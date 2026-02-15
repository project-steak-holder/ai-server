from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel


class MessageType(str, Enum):
    ai = "ai"
    user = "user"


class GenerateRequest(BaseModel):
    conversation_id: str
    content: str


class GenerateResponse(BaseModel):
    conversation_id: str
    content: str
    type: MessageType
    created_at: datetime
    updated_at: datetime
