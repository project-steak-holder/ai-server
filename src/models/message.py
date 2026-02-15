from datetime import datetime
from enum import Enum as PyEnum
from uuid import uuid4

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Index, String, Text
from sqlalchemy.orm import relationship

from .base import Base


class MessageType(str, PyEnum):
    USER = "USER"
    AI = "AI"


class Message(Base):
    __tablename__ = "message"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    conversation_id = Column(String(36), ForeignKey("conversation.id"), nullable=False)
    user_id = Column(String(36), ForeignKey("user.id"), nullable=False)
    content = Column(Text, nullable=False)
    type = Column(Enum(MessageType), nullable=False)
    createdAt = Column(DateTime, default=datetime.utcnow, nullable=False)
    updatedAt = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    conversation = relationship("Conversation", back_populates="messages")
    user = relationship("User", back_populates="messages")


Index("ix_message_user_id", Message.user_id)
Index(
    "ix_message_conversation_createdAt",
    Message.conversation_id,
    Message.createdAt,
)
