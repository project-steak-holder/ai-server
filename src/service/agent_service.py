"""
AgentService: Main service for agentic AI stakeholder simulation.
This service will orchestrate conversation flow,
persistence, persona, project context, and LLM interaction for a project stakeholder agent.
"""

import json
from typing import AsyncGenerator
from pydantic_ai import ModelMessage
from pydantic import ValidationError

from src.agents.stakeholder_agent import (
    run_stakeholder_query,
    run_stakeholder_query_stream,
)
from src.exceptions.llm_response_exception import LlmResponseException
from src.middlewares.events import wide_event
from src.schemas.message_model import Message
from src.schemas.persona_model import Persona
from src.schemas.project_model import Project
from src.service.history_compactor_service import HistoryCompactorService
from src.service.model_service import ModelService
from src.service.message_service import MessageService


class AgentService:
    """Service for orchestrating agent conversations and context."""

    def __init__(
        self,
        model_service: ModelService,
        message_service: MessageService,
    ) -> None:
        # dependencies injected via FastAPI
        self.model_service: ModelService = model_service
        self.message_service: MessageService = message_service
        self.request: str | None = None
        self.conversation_id: str | None = None

    def load_persona(self) -> Persona:
        """loads persona model from model service"""
        result = self.model_service.get_model("persona")
        if not isinstance(result, Persona):
            raise TypeError(f"Expected Persona, got {type(result).__name__}")
        return result

    def load_project(self) -> Project:
        """loads project model from model service"""
        result = self.model_service.get_model("project")
        if not isinstance(result, Project):
            raise TypeError(f"Expected Project, got {type(result).__name__}")
        return result

    async def load_history(self, user_id: str, conversation_id: str) -> list[Message]:
        """loads from message service"""
        db_messages = await self.message_service.get_conversation_history(
            user_id=user_id, conversation_id=conversation_id
        )
        try:
            return [
                Message.model_validate(msg, from_attributes=True) for msg in db_messages
            ]
        except ValidationError as ve:
            # Optionally, you could raise a custom exception here for clarity
            raise Exception(f"Validation error in message history: {ve}") from ve

    def set_request(self, request: str) -> None:
        """set from request payload in orchestrator method"""
        self.request = request

    def set_conversation_id(self, conversation_id: str) -> None:
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

        try:
            response_content = await run_stakeholder_query(
                message=content,
                persona=persona,
                project=project,
                history=compacted_history,
            )
        except LlmResponseException:
            error_message = (
                "I'm sorry, I encountered an error and was unable to respond."
            )
            await self.message_service.save_ai_message(
                user_id=user_id, conversation_id=conversation_id, content=error_message
            )
            raise

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

        except LlmResponseException:
            error_message = (
                "I'm sorry, I encountered an error and was unable to respond."
            )
            await self.message_service.save_ai_message(
                user_id=user_id, conversation_id=conversation_id, content=error_message
            )
            yield f"data: {json.dumps({'error': error_message})}\n\n"
