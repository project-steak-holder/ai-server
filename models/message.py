from sqlalchemy import Column, Integer, Text, String, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from enum import Enum as PyEnum
from datetime import datetime
from .base import Base

class Role(str, PyEnum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"

class Message(Base):
    __tablename__ = "messages"
    
    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), index=True)
    role = Column(Role, index=True)
    content = Column(Text)  # Raw message (NOT compacted)
    model = Column(String(100))  # "llama3.1-8b"
    tokens_used = Column(Integer)  # For cost tracking
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    conversation = relationship("Conversation", back_populates="messages")
