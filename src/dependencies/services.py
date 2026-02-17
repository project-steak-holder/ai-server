"""Service dependencies for FastAPI dependency injection."""

from typing import Annotated

from fastapi import Depends

from src.service.agent_service import AgentService as AgentServiceClass
from src.service.persona_service import PersonaService as PersonaServiceClass
from src.service.project_service import ProjectService as ProjectServiceClass
from src.service.message_service import MessageService as MessageServiceClass
from src.dependencies.database import get_message_service


def get_persona_service() -> PersonaServiceClass:
    """Get PersonaService instance."""
    return PersonaServiceClass()


def get_project_service() -> ProjectServiceClass:
    """Get ProjectService instance."""
    return ProjectServiceClass()


def get_agent_service(
    message_service: Annotated[MessageServiceClass, Depends(get_message_service)],
) -> AgentServiceClass:
    """Get AgentService instance with injected dependencies."""
    return AgentServiceClass(
        message_service=message_service,
        persona_service=get_persona_service(),
        project_service=get_project_service(),
    )


# Type aliases for dependency injection
PersonaService = Annotated[PersonaServiceClass, Depends(get_persona_service)]
ProjectService = Annotated[ProjectServiceClass, Depends(get_project_service)]
AgentService = Annotated[AgentServiceClass, Depends(get_agent_service)]
