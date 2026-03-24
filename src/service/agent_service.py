"""
AgentService: Main service for agentic AI stakeholder simulation.
This service will orchestrate conversation flow,
persistence, persona, project context, and LLM interaction for a project stakeholder agent.
"""

import json
from typing import AsyncGenerator
from pydantic_ai import ModelMessage

from src.agents.stakeholder_agent import (
    run_stakeholder_query,
    run_stakeholder_query_stream,
)
from src.exceptions.llm_response_exception import LlmResponseException
from src.middlewares.events import wide_event
from src.schemas.message_model import Message
from src.service.history_compactor_service import HistoryCompactorService
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
        self.request: str | None = None
        self.conversation_id: str | None = None

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
        db_messages = await self.message_service.get_conversation_history(
            user_id=user_id, conversation_id=conversation_id
        )

        return [
            Message.model_validate(msg, from_attributes=True) for msg in db_messages
        ]

    def set_request(self, request: str):
        """set from request payload in orchestrator method"""
        self.request = request

    def set_conversation_id(self, conversation_id: str):
        """set from request payload in orchestrator method"""
        self.conversation_id = conversation_id

    @wide_event("process_agent_query")
    async def process_agent_query(
        self, user_id: str, conversation_id: str, content: str
    ) -> str:
        """Main Orchestrator Method
        receives request payload from controller as dict
        assembles context from persona, project and persistence(history) service
        persists both request and response messages via persistence service
        returns response to controller as dict
        """
        await self.message_service.save_user_message(
            user_id=user_id,
            conversation_id=conversation_id,
            content=content,
        )

        persona = self.load_persona()
        project = self.load_project()
        history = await self.load_history(user_id, conversation_id)  # list[Message]
        compacted_history: list[
            ModelMessage
        ] = await HistoryCompactorService.summarize_old_messages(history)

        response_content = await run_stakeholder_query(
            message=content,
            persona=persona,
            project=project,
            history=compacted_history,
        )

        await self.message_service.save_ai_message(
            user_id=user_id,
            conversation_id=conversation_id,
            content=response_content,
        )

        return response_content

    @wide_event("process_agent_query_stream")
    async def process_agent_query_stream(
        self, user_id: str, conversation_id: str, content: str
    ) -> AsyncGenerator[str, None]:
        """Stream agent response maintaining architectural consistency."""

        # Save user message
        await self.message_service.save_user_message(
            user_id=user_id, conversation_id=conversation_id, content=content
        )

        # Load context (same as v1)
        persona = self.load_persona()
        project = self.load_project()
        history = await self.load_history(
            user_id=user_id, conversation_id=conversation_id
        )
        compacted_history = await HistoryCompactorService.summarize_old_messages(
            messages=history
        )

        # Stream through agent layer
        full_response = ""
        try:
            async for chunk in run_stakeholder_query_stream(
                message=content,
                persona=persona,
                project=project,
                history=compacted_history,
            ):
                full_response += chunk
                yield f"data: {json.dumps({'content': chunk, 'partial': True})}\n\n"

            # Save complete response
            await self.message_service.save_ai_message(
                user_id=user_id, conversation_id=conversation_id, content=full_response
            )
            yield f"data: {json.dumps({'complete': True})}\n\n"

        except LlmResponseException as e:
            yield f"data: {json.dumps({'error': str(e), 'details': e.details or {}})}\n\n"
