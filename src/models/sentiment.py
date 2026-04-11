import uuid
from .base import Base
from sqlalchemy import (
    UUID,
    Column,
    Numeric,
    ForeignKey,
    Index,
    CheckConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column


class Sentiment(Base):
    __tablename__ = "sentiment"
    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    conversation_id = Column(
        UUID,
        ForeignKey("conversation.id"),
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
