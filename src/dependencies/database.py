"""Database dependencies for FastAPI dependency injection."""

from typing import Annotated
from fastapi import Depends

from src.database import DatabaseSession
from src.repository.message_repository import (
    MessageRepository as MessageRepositoryClass,
)


from src.repository.sentiment_repository import (
    SentimentRepository as SentimentRepositoryClass,
)

from src.repository.summary_repository import (
    SummaryRepository as SummaryRepositoryClass,
)


def get_message_repository(session: DatabaseSession) -> MessageRepositoryClass:
    """Get MessageRepository instance with injected database session."""
    return MessageRepositoryClass(session)


def get_sentiment_repository(session: DatabaseSession) -> SentimentRepositoryClass:
    """Get SentimentRepository instance with injected database session."""
    return SentimentRepositoryClass(session)


def get_summary_repository(session: DatabaseSession) -> SummaryRepositoryClass:
    """Get SummaryRepository instance with injected database session."""
    return SummaryRepositoryClass(session)


# Type aliases for dependency injection
MessageRepository = Annotated[MessageRepositoryClass, Depends(get_message_repository)]
SentimentRepository = Annotated[
    SentimentRepositoryClass, Depends(get_sentiment_repository)
]
SummaryRepository = Annotated[SummaryRepositoryClass, Depends(get_summary_repository)]
