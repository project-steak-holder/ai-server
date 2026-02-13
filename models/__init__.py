from datetime import datetime
from enum import Enum as PyEnum
from .conversation import Conversation
from .message import Message
from .user import User  # Neon Auth handles this

__all__ = ['Conversation', 'Message', 'User']


from sqlalchemy import (
    Column,
    String,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Text,
    Index,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class MessageType(PyEnum):
    USER = "USER"
    AI = "AI"


class User(Base):
    __tablename__ = "user"
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    email = Column(String, nullable=False, unique=True)
    emailVerified = Column(Boolean, nullable=False, default=False)
    image = Column(String)
    createdAt = Column(DateTime, default=datetime.utcnow, nullable=False)
    updatedAt = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )
    conversations = relationship("Conversation", back_populates="user")
    messages = relationship("Message", back_populates="user")


class Conversation(Base):
    __tablename__ = "conversation"
    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("user.id"), nullable=False)
    name = Column(String, nullable=False)
    createdAt = Column(DateTime, default=datetime.utcnow, nullable=False)
    updatedAt = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )
    user = relationship("User", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation")


class Message(Base):
    __tablename__ = "message"
    id = Column(String, primary_key=True)
    conversation_id = Column(String, ForeignKey("conversation.id"), nullable=False)
    user_id = Column(String, ForeignKey("user.id"), nullable=False)
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
