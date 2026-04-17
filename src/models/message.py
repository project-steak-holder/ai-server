import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    UUID,
    Text,
    DateTime,
    ForeignKey,
    Enum as SQLEnum,
    Index,
)
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base
from src.schemas.message_model import MessageType


class Message(Base):
    __tablename__ = "message"
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        ForeignKey("conversation.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        ForeignKey("neon_auth.user.id"),
        nullable=False,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    type: Mapped[MessageType] = mapped_column(SQLEnum(MessageType), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    __table_args__ = (
        Index("ix_message_conversation_created_at", "conversation_id", "created_at"),
    )
