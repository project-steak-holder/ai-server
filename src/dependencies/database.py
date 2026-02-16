"""Database dependencies for FastAPI dependency injection."""

from typing import Annotated
from fastapi import Depends

from src.database import DatabaseSession
from src.repository.model_repository import MessageRepository as MessageRepositoryClass
from src.service.message_service import MessageService as MessageServiceClass


def get_message_repository(session: DatabaseSession) -> MessageRepositoryClass:
    """Get MessageRepository instance with injected database session."""
    return MessageRepositoryClass(session)


def get_message_service(
    repository: Annotated[MessageRepositoryClass, Depends(get_message_repository)],
) -> MessageServiceClass:
    """Get MessageService instance with injected repository."""
    return MessageServiceClass(repository)


# Type aliases for dependency injection
MessageRepository = Annotated[MessageRepositoryClass, Depends(get_message_repository)]
MessageService = Annotated[MessageServiceClass, Depends(get_message_service)]
