import uuid
from sqlalchemy import (
    UUID,
    Column,
    Integer,
    Text,
    DateTime,
    ForeignKey,
)

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
    content = Column(Text, nullable=True)
    token_count = Column(
        Integer,
        default=0,
        server_default="0",
        nullable=False,
    )
    window_start = Column(
        DateTime(timezone=True),
        nullable=True,
    )
    window_end = Column(
        DateTime(timezone=True),
        nullable=True,
    )
