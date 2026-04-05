"""Database dependencies for FastAPI dependency injection."""

from typing import Annotated
from fastapi import Depends

from src.database import DatabaseSession
from src.repository.message_repository import (
    MessageRepository as MessageRepositoryClass,
)
from src.service.message_service import MessageService as MessageServiceClass
from src.repository.sentiment_repository import (
    SentimentRepository as SentimentRepositoryClass,
)
from src.service.sentiment_service import (
    SentimentService as SentimentServiceClass,
)


def get_message_repository(session: DatabaseSession) -> MessageRepositoryClass:
    """Get MessageRepository instance with injected database session."""
    return MessageRepositoryClass(session)


def get_sentiment_repository(session: DatabaseSession) -> SentimentRepositoryClass:
    """Get SentimentRepository instance with injected database session."""
    return SentimentRepositoryClass(session)


def get_message_service(
    repository: Annotated[MessageRepositoryClass, Depends(get_message_repository)],
) -> MessageServiceClass:
    """Get MessageService instance with injected repository."""
    return MessageServiceClass(repository)


def get_sentiment_service(
    repository: Annotated[SentimentRepositoryClass, Depends(get_sentiment_repository)],
) -> SentimentServiceClass:
    """Get SentimentService instance with injected repository."""
    return SentimentServiceClass(repository)


# Type aliases for dependency injection
MessageRepository = Annotated[MessageRepositoryClass, Depends(get_message_repository)]
MessageService = Annotated[MessageServiceClass, Depends(get_message_service)]
SentimentRepository = Annotated[
    SentimentRepositoryClass, Depends(get_sentiment_repository)
]
SentimentService = Annotated[SentimentServiceClass, Depends(get_sentiment_service)]
