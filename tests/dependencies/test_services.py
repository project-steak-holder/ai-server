"""Unit tests for service dependency factories."""

from unittest.mock import MagicMock, patch

from src.dependencies.services import (
    get_agent_service,
    get_persona_service,
    get_project_service,
)


def test_dependencies_service_factories():
    persona_service = get_persona_service()
    project_service = get_project_service()

    assert persona_service.__class__.__name__ == "PersonaService"
    assert project_service.__class__.__name__ == "ProjectService"

    message_service = MagicMock()
    with (
        patch("src.dependencies.services.get_persona_service", return_value="persona"),
        patch("src.dependencies.services.get_project_service", return_value="project"),
    ):
        agent_service = get_agent_service(message_service)

    assert agent_service.message_service is message_service
    assert agent_service.persona_service == "persona"
    assert agent_service.project_service == "project"
