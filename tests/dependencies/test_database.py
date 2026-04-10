"""Unit tests for database dependency factories."""

from unittest.mock import MagicMock

from src.dependencies import (
    get_message_repository,
    get_sentiment_repository,
)

from src.repository.message_repository import MessageRepository
from src.repository.sentiment_repository import SentimentRepository


def test_dependencies_database_factories():
    session = MagicMock()
    message_repo = get_message_repository(session)
    sentiment_repo = get_sentiment_repository(session)

    assert isinstance(message_repo, MessageRepository)
    assert isinstance(sentiment_repo, SentimentRepository)

    assert message_repo.session is session
    assert sentiment_repo.session is session
