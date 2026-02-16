"""
AgentService: Main service for agentic AI stakeholder simulation.
This service will orchestrate conversation flow,
persistence, persona, project context, and LLM interaction for a project stakeholder agent.
"""

from src.agents.stakeholder_agent import run_stakeholder_query
from src.schemas.message_model import Message
from src.service.persona_service import PersonaService
from src.service.project_service import ProjectService
from src.service.message_service import MessageService


class AgentService:
    """Service for orchestrating agent conversations and context."""

    def __init__(
        self,
        persona_service: PersonaService,
        project_service: ProjectService,
        message_service: MessageService,
    ):
        # dependencies injected via FastAPI
        self.persona_service = persona_service
        self.project_service = project_service
        self.message_service = message_service

    def load_persona(self):
        """loads from persona service"""
        self.persona_service.load_persona()
        return self.persona_service.get_persona()

    def load_project(self):
        """loads from project service"""
        self.project_service.load_project()
        return self.project_service.get_project()

    async def load_history(self, user_id: str, conversation_id: str):
        """loads from message service"""
        history = await self.message_service.get_conversation_history(
            user_id=user_id, conversation_id=conversation_id
        )
        return [Message.model_validate(msg, from_attributes=True) for msg in history]

    def set_request(self, request: str):
        """set from request payload in orchestrator method"""
        self.request = request

    def set_conversation_id(self, conversation_id: str):
        """set from request payload in orchestrator method"""
        self.conversation_id = conversation_id

    async def process_agent_query(
        self, user_id: str, conversation_id: str, content: str
    ) -> dict:
        """Main Orchestrator Method
        receives request payload from controller as dict
        assembles context from persona, project and persistence(history) service
        persists both request and response messages via persistence service
        returns response to controller as dict
        """
        # Save the users message
        user_message = await self.message_service.save_user_message(
            user_id=user_id,
            conversation_id=conversation_id,
            content=content,
        )
        if user_message is None:
            return {
                "event": {
                    "process_agent_query": "error",
                    "process_agent_query_detail": "failed to save user message",
                }
            }
        # load context
        persona = self.load_persona()
        project = self.load_project()
        history = await self.load_history(user_id, conversation_id)

        # validate context
        if not all([persona, project]):
            return {
                "event": {
                    "process_agent_query": "error",
                    "process_agent_query_detail": "missing required context",
                }
            }

        # Run PydanticAI agent
        try:
            response_content = await run_stakeholder_query(
                message=content,
                persona=persona,
                project=project,
                history=history or [],
            )
        except Exception as e:
            return {
                "event": {
                    "process_agent_query": "error",
                    "process_agent_query_detail": f"LLM error: {str(e)}",
                }
            }

        if not response_content:
            return {
                "event": {
                    "process_agent_query": "error",
                    "process_agent_query_detail": "LLM response missing 'message' field",
                }
            }

        # persist response
        saved_ai_message = await self.message_service.save_ai_message(
            user_id=user_id,
            conversation_id=conversation_id,
            content=response_content,
        )
        if saved_ai_message is None:
            return {
                "event": {
                    "process_agent_query": "error",
                    "process_agent_query_detail": "failed to save AI message",
                }
            }

        return {
            "event": {
                "process_agent_query": "success",
                "process_agent_query_detail": "AI message saved successfully",
            },
            "response": saved_ai_message.content,
        }
