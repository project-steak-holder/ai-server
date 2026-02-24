"""Unit tests for database dependency factories."""

from unittest.mock import MagicMock

from src.dependencies.database import get_message_repository, get_message_service
from src.repository.model_repository import MessageRepository


def test_dependencies_database_factories():
    session = MagicMock()
    repo = get_message_repository(session)
    service = get_message_service(repo)

    assert isinstance(repo, MessageRepository)
    assert repo.session is session
    assert service.message_repository is repo
