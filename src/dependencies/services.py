"""Service dependencies for FastAPI dependency injection."""

from typing import Annotated

from fastapi import Depends
from functools import lru_cache

from src.service.agent_service import AgentService as AgentServiceClass
from src.service.model_service import ModelService as ModelServiceClass
from src.service.message_service import MessageService as MessageServiceClass
from src.service.sentiment_service import (
    SentimentService as SentimentServiceClass,
)
from src.service.history_compactor_service import (
    HistoryCompactorService as HistoryCompactorServiceClass,
)
from src.service.summary_service import SummaryService as SummaryServiceClass

from src.dependencies import (
    get_message_repository,
    get_sentiment_repository,
    get_summary_repository,
    MessageRepositoryClass,
    SentimentRepositoryClass,
    SummaryRepositoryClass,
)


@lru_cache()
def get_model_service() -> ModelServiceClass:
    """Get ModelService singleton instance (cached)."""
    return ModelServiceClass()


@lru_cache()
def get_history_compactor_service() -> HistoryCompactorServiceClass:
    """Get HistoryCompactorService singleton instance (cached). Used by background tasks."""
    return HistoryCompactorServiceClass()


def get_message_service(
    repository: Annotated[MessageRepositoryClass, Depends(get_message_repository)],
) -> MessageServiceClass:
    """Get MessageService instance with injected repository."""
    return MessageServiceClass(repository)


def get_sentiment_service(
    sentiment_repository: Annotated[
        SentimentRepositoryClass, Depends(get_sentiment_repository)
    ],
    model_service: Annotated[ModelServiceClass, Depends(get_model_service)],
) -> SentimentServiceClass:
    """Get SentimentService instance with injected repository."""
    return SentimentServiceClass(
        sentiment_repository=sentiment_repository, model_service=model_service
    )


def get_summary_service(
    summary_repository: Annotated[
        SummaryRepositoryClass, Depends(get_summary_repository)
    ],
) -> SummaryServiceClass:
    """Get SummaryService instance with injected repository."""
    return SummaryServiceClass(summary_repository=summary_repository)


def get_agent_service(
    model_service: Annotated[ModelServiceClass, Depends(get_model_service)],
    message_service: Annotated[MessageServiceClass, Depends(get_message_service)],
    sentiment_service: Annotated[SentimentServiceClass, Depends(get_sentiment_service)],
    summary_service: Annotated[SummaryServiceClass, Depends(get_summary_service)],
) -> AgentServiceClass:
    """Get AgentService instance with injected dependencies."""
    return AgentServiceClass(
        model_service=model_service,
        message_service=message_service,
        sentiment_service=sentiment_service,
        summary_service=summary_service,
    )


# Type aliases for dependency injection
ModelService = Annotated[ModelServiceClass, Depends(get_model_service)]
AgentService = Annotated[AgentServiceClass, Depends(get_agent_service)]
SentimentService = Annotated[SentimentServiceClass, Depends(get_sentiment_service)]
MessageService = Annotated[MessageServiceClass, Depends(get_message_service)]
SummaryService = Annotated[SummaryServiceClass, Depends(get_summary_service)]
