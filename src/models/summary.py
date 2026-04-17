import uuid
from datetime import datetime
from sqlalchemy import (
    UUID,
    Column,
    Integer,
    Text,
    DateTime,
    ForeignKey,
)
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class Summary(Base):
    __tablename__ = "summary"
    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    conversation_id = Column(
        UUID,
        ForeignKey("conversation.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    token_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default="0",
        nullable=False,
    )
    window_start: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    window_end: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
