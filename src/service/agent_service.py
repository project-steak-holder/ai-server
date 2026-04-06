"""
AgentService: Main service for agentic AI stakeholder simulation.
This service will orchestrate conversation flow,
persistence, persona, project context, and LLM interaction for a project stakeholder agent.
"""

import json
import re
from typing import AsyncGenerator, Optional
from pydantic_ai import ModelMessage
from pydantic import ValidationError

from src.exceptions.llm_response_exception import LlmResponseException
from src.middlewares.events import add_event_context, wide_event
from src.schemas.message_model import Message
from src.schemas.persona_model import Persona
from src.schemas.project_model import Project
from src.schemas.sentiment_scale_model import SentimentScale
from src.schemas.listening_cues_model import ListeningCues
from src.schemas.instructions_model import InstructionsModel
from src.service.history_compactor_service import HistoryCompactorService
from src.service.model_service import ModelService
from src.service.message_service import MessageService
from src.agents.stakeholder_agent import (
    run_stakeholder_query_stream as _run_stakeholder_query_stream,
    AgentResponse,
)


class AgentService:
    """Service for orchestrating agent conversations and context."""

    def __init__(
        self,
        model_service: ModelService,
        message_service: MessageService,
        sentiment_service,
    ) -> None:
        self.model_service: ModelService = model_service
        self.message_service: MessageService = message_service
        self.sentiment_service = sentiment_service
        self.request: Optional[str] = None
        self.conversation_id: Optional[str] = None

    def load_persona(self) -> Persona:
        """loads persona model from model service"""
        result = self.model_service.get_model("persona")

        if not isinstance(result, Persona):
            raise TypeError(f"Expected Persona, got {type(result).__name__}")
        add_event_context(persona_name=result.name)
        return result

    def load_project(self) -> Project:
        """loads project model from model service"""
        result = self.model_service.get_model("project")
        if not isinstance(result, Project):
            raise TypeError(f"Expected Project, got {type(result).__name__}")
        add_event_context(project_name=result.project_name)
        return result

    def load_sentiment_scale(self):
        """loads sentiment_scale model from model service"""
        result = self.model_service.get_model("sentiment_scale")
        if not isinstance(result, SentimentScale):
            raise TypeError(f"Expected SentimentScale, got {type(result).__name__}")
        return result

    def load_listening_cues(self):
        """loads listening_cues model from model service"""
        result = self.model_service.get_model("listening_cues")
        if not isinstance(result, ListeningCues):
            raise TypeError(f"Expected ListeningCues, got {type(result).__name__}")
        return result

    def load_instructions(self):
        """loads instructions model from model service"""
        result = self.model_service.get_model("instructions")
        if not isinstance(result, InstructionsModel):
            raise TypeError(f"Expected InstructionsModel, got {type(result).__name__}")
        return result

    async def load_history(self, user_id: str, conversation_id: str) -> list[Message]:
        """loads from message service"""
        db_messages = await self.message_service.get_conversation_history(
            user_id=user_id, conversation_id=conversation_id
        )
        add_event_context(history_length=len(db_messages))
        try:
            return [
                Message.model_validate(msg, from_attributes=True) for msg in db_messages
            ]
        except ValidationError as ve:
            raise Exception(f"Validation error in message history: {ve}") from ve

    def set_request(self, request: str) -> None:
        """set from request payload in orchestrator method"""
        self.request = request

    def set_conversation_id(self, conversation_id: str) -> None:
        """set from request payload in orchestrator method"""
        self.conversation_id = conversation_id

    async def save_user_message(
        self, user_id: str, conversation_id: str, content: str
    ) -> Message:
        """Persist the user's message via message service."""
        return Message.model_validate(
            await self.message_service.save_user_message(
                user_id=user_id,
                conversation_id=conversation_id,
                content=content,
            ),
            from_attributes=True,
        )

    async def save_ai_message(
        self, user_id: str, conversation_id: str, content: str
    ) -> Message:
        """Persist an AI message via message service."""
        return Message.model_validate(
            await self.message_service.save_ai_message(
                user_id=user_id,
                conversation_id=conversation_id,
                content=content,
            ),
            from_attributes=True,
        )

    async def run_stakeholder_query_stream(
        self, content: str, history: list[Message], persona: Persona
    ) -> AsyncGenerator[str, None]:
        """Load context, compact history, and stream agent response chunks."""
        project = self.load_project()
        sentiment_scale = self.load_sentiment_scale()
        listening_cues = self.load_listening_cues()
        instructions = self.load_instructions()
        compacted_history: list[
            ModelMessage
        ] = await HistoryCompactorService.summarize_old_messages(history)
        async for chunk in _run_stakeholder_query_stream(
            message=content,
            persona=persona,
            project=project,
            history=compacted_history,
            sentiment_scale=sentiment_scale,
            listening_cues=listening_cues,
            instructions=instructions,
        ):
            yield chunk

    @wide_event("process_agent_query_stream")
    async def process_agent_query_stream(
        self, user_id: str, conversation_id: str, content: str
    ) -> AsyncGenerator[str, None]:
        """Stream agent response maintaining architectural consistency, with robust error handling for history loading."""

        history = await self.load_history(
            user_id=user_id, conversation_id=conversation_id
        )

        await self.save_user_message(
            user_id=user_id, conversation_id=conversation_id, content=content
        )

        # Get persona copy with sentiment injected
        persona = self.load_persona()
        persona_with_sentiment = (
            await self.sentiment_service.get_persona_w_current_sentiment(
                persona, conversation_id
            )
        )
        # get current sentiment value for update with delta later
        current_sentiment = await self.sentiment_service.get_current_sentiment_value(
            conversation_id
        )

        full_response = ""
        try:
            async for chunk in self.run_stakeholder_query_stream(
                content, history, persona_with_sentiment
            ):
                full_response += chunk
                yield f"data: {json.dumps({'content': chunk, 'partial': True})}\n\n"

            add_event_context(ai_response_length=len(full_response))

            # Try to parse the full response as AgentResponse
            try:
                response_obj = AgentResponse.model_validate(json.loads(full_response))
            except (json.JSONDecodeError, ValidationError, TypeError, ValueError):
                response_obj = None

            # get delta from LLM response
            sentiment_delta = (
                getattr(response_obj, "sentiment", None) if response_obj else None
            )
            # apply delta and persist using SentimentService
            await self.sentiment_service.apply_delta(
                conversation_id, current_sentiment, sentiment_delta
            )
            yield f"data: {json.dumps({'complete': True})}\n\n"

        except LlmResponseException as e:
            full_response = (
                "I'm sorry, I encountered an error and was unable to respond."
            )
            print(f"[DEBUG] LlmResponseException: {e}")
            add_event_context(error_type="LlmResponseException", error_message=str(e))
            yield f"data: {json.dumps({'error': full_response})}\n\n"

        except Exception as e:
            full_response = "I'm sorry, I encountered an unexpected error and was unable to respond."
            print(f"[DEBUG] Unexpected exception: {e}")
            add_event_context(error_type="UnexpectedException", error_message=str(e))
            yield f"data: {json.dumps({'error': full_response})}\n\n"

        finally:
            # Strip <think>...</think> tags from the accumulated response before saving
            if full_response:
                # Remove all <think>...</think> tags (non-greedy)
                full_response = re.sub(
                    r"<think>.*?</think>", "", full_response, flags=re.DOTALL
                )
                full_response = full_response.strip()
            await self.save_ai_message(
                user_id=user_id, conversation_id=conversation_id, content=full_response
            )
