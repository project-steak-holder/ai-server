"""Service dependencies for FastAPI dependency injection."""

from typing import Annotated

from fastapi import Depends

from src.service.agent_service import AgentService as AgentServiceClass
from src.service.model_service import ModelService as ModelServiceClass
from functools import lru_cache
from src.service.message_service import MessageService as MessageServiceClass
from src.service.sentiment_data_service import (
    SentimentDataService as SentimentDataServiceClass,
)
from src.dependencies.database import get_message_service, get_sentiment_service


@lru_cache()
def get_model_service() -> ModelServiceClass:
    """Get ModelService singleton instance (cached)."""
    return ModelServiceClass()


def get_agent_service(
    model_service: Annotated[ModelServiceClass, Depends(get_model_service)],
    message_service: Annotated[MessageServiceClass, Depends(get_message_service)],
) -> AgentServiceClass:
    """Get AgentService instance with injected dependencies."""
    return AgentServiceClass(
        model_service=model_service,
        message_service=message_service,
    )


get_sentiment_data_service = Depends(get_sentiment_service)


# Type aliases for dependency injection
ModelService = Annotated[ModelServiceClass, Depends(get_model_service)]
AgentService = Annotated[AgentServiceClass, Depends(get_agent_service)]
SentimentDataService = Annotated[SentimentDataServiceClass, get_sentiment_data_service]
