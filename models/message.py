from sqlalchemy import Column, Integer, Text, String, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from enum import Enum as PyEnum
from datetime import datetime
from .base import Base
from sqlalchemy.dialects.postgresql import UUID
import uuid

class MessageType(str, PyEnum):
    USER = "user"
    AI = "ai"

class Message(Base):
    __tablename__ = "messages"
    
    from sqlalchemy.dialects.postgresql import UUID
    import uuid

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(UUID(as_uuid=True), 
    ForeignKey("conversations.id"), index=True)  
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)   
    type = Column(Enum(MessageType), nullable=False, default=MessageType.USER)
    content = Column(Text)  # Raw message (NOT compacted)
    model = Column(String(100))  # "llama3.1-8b"
    tokens_used = Column(Integer)  # For cost tracking
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    conversation = relationship("Conversation", back_populates="messages")
