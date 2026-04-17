import uuid

from sqlalchemy import (
    UUID,
    Numeric,
    ForeignKey,
    Index,
    CheckConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class Sentiment(Base):
    __tablename__ = "sentiment"
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        ForeignKey("conversation.id", ondelete="CASCADE"),
        nullable=False,
    )
    sentiment: Mapped[float] = mapped_column(
        Numeric(4, 2, asdecimal=False),
        nullable=False,
        default=0.00,
    )
    __table_args__ = (
        Index("ix_sentiment_conversation_id", "conversation_id"),
        CheckConstraint(
            "sentiment >= -10.00 AND sentiment <= 10.00", name="ck_sentiment_range"
        ),
    )
