from datetime import datetime, timezone
import uuid

from sqlalchemy.orm import Mapped, mapped_column
from .base import Base

from sqlalchemy import (
    UUID,
    Column,
    Text,
    DateTime,
    ForeignKey,
    Enum as SQLEnum,
    Index,
)

from src.schemas.message_model import MessageType


class Message(Base):
    __tablename__ = "message"
    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    conversation_id = Column(
        UUID,
        ForeignKey("conversation.id"),
        nullable=False,
    )
    user_id = Column(
        UUID,
        ForeignKey("neon_auth.user.id"),
        nullable=False,
    )
    content = Column(Text, nullable=False)
    type: Mapped[MessageType] = mapped_column(SQLEnum(MessageType), nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    __table_args__ = (
        Index("ix_message_conversation_created_at", "conversation_id", "created_at"),
    )
