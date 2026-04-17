import uuid
from datetime import datetime

from sqlalchemy import (
    UUID,
    Integer,
    Text,
    DateTime,
    ForeignKey,
)
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class Summary(Base):
    __tablename__ = "summary"
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        ForeignKey("conversation.id", ondelete="CASCADE"),
        unique=True,
    )
    content: Mapped[str | None] = mapped_column(Text)
    token_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default="0",
    )
    window_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    window_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
