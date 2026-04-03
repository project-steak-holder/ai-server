"""
AgentService: Main service for agentic AI stakeholder simulation.
This service will orchestrate conversation flow,
persistence, persona, project context, and LLM interaction for a project stakeholder agent.
"""

import json
import re
from decimal import Decimal, InvalidOperation
from typing import AsyncGenerator
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
from src.service.persona_with_sentiment import get_persona_with_sentiment
from src.agents.stakeholder_agent import (
    run_stakeholder_query as _run_stakeholder_query,
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
        self.request: str | None = None
        self.conversation_id: str | None = None

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

    @wide_event("run_stakeholder_query")
    async def run_stakeholder_query(
        self, content: str, history: list[Message], persona: Persona
    ):
        """Load context, compact history, and run the agent. Returns AgentResponse object."""
        project = self.load_project()
        sentiment_scale = self.load_sentiment_scale()
        listening_cues = self.load_listening_cues()
        instructions = self.load_instructions()
        compacted_history: list[
            ModelMessage
        ] = await HistoryCompactorService.summarize_old_messages(history)
        return await _run_stakeholder_query(
            message=content,
            persona=persona,
            project=project,
            history=compacted_history,
            sentiment_scale=sentiment_scale,
            listening_cues=listening_cues,
            instructions=instructions,
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

        history = await self.load_history(user_id, conversation_id)

        persona = self.load_persona()
        persona_with_sentiment = await get_persona_with_sentiment(
            persona, self.sentiment_service, conversation_id
        )

        agent_response = await self.run_stakeholder_query(
            content, history, persona_with_sentiment
        )

        # If agent_response is a string, treat as content only
        if isinstance(agent_response, str):
            content_to_save = agent_response
            sentiment_delta = None
        else:
            content_to_save = getattr(agent_response, "content", str(agent_response))
            sentiment_delta = getattr(agent_response, "sentiment", None)

        # Strip <think> tags from content before saving (robust, handles multiple tags and whitespace)
        content_to_save = re.sub(
            r"<think>.*?</think>", "", content_to_save, flags=re.DOTALL | re.IGNORECASE
        )
        content_to_save = re.sub(r"\s+", " ", content_to_save).strip()

        # Retrieve current sentiment from DB
        sentiment_obj = await self.sentiment_service.get_sentiment(conversation_id)
        current_sentiment = (
            Decimal(str(sentiment_obj.sentiment))
            if sentiment_obj and sentiment_obj.sentiment is not None
            else Decimal("0.00")
        )

        # Validate and parse delta
        try:
            delta = (
                Decimal(str(sentiment_delta))
                if sentiment_delta is not None
                else Decimal("0.00")
            )
        except (InvalidOperation, ValueError):
            delta = Decimal("0.00")

        # Compute updated sentiment and clamp
        updated_sentiment = current_sentiment + delta
        updated_sentiment = max(
            Decimal("-10.00"), min(Decimal("10.00"), updated_sentiment)
        )

        # Persist updated sentiment
        await self.sentiment_service.update_sentiment(
            conversation_id, updated_sentiment
        )

        await self.save_user_message(
            user_id=user_id,
            conversation_id=conversation_id,
            content=content,
        )

        await self.save_ai_message(
            user_id=user_id,
            conversation_id=conversation_id,
            content=content_to_save,
        )

        return content_to_save

    @wide_event("process_agent_query_stream")
    async def process_agent_query_stream(
        self, user_id: str, conversation_id: str, content: str
    ) -> AsyncGenerator[str, None]:
        """Stream agent response maintaining architectural consistency."""

        history = await self.load_history(
            user_id=user_id, conversation_id=conversation_id
        )

        await self.save_user_message(
            user_id=user_id, conversation_id=conversation_id, content=content
        )

        persona = self.load_persona()
        persona_with_sentiment = await get_persona_with_sentiment(
            persona, self.sentiment_service, conversation_id
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

            # Retrieve current sentiment from DB
            sentiment_obj = await self.sentiment_service.get_sentiment(conversation_id)
            current_sentiment = (
                Decimal(str(sentiment_obj.sentiment))
                if sentiment_obj and sentiment_obj.sentiment is not None
                else Decimal("0.00")
            )

            # Validate and parse delta
            sentiment_delta = (
                getattr(response_obj, "sentiment", None) if response_obj else None
            )
            try:
                delta = (
                    Decimal(str(sentiment_delta))
                    if sentiment_delta is not None
                    else Decimal("0.00")
                )
            except (InvalidOperation, ValueError):
                delta = Decimal("0.00")
                # Optionally log error here

            # Compute updated sentiment and clamp
            updated_sentiment = current_sentiment + delta
            updated_sentiment = max(
                Decimal("-10.00"), min(Decimal("10.00"), updated_sentiment)
            )

            # Persist updated sentiment
            await self.sentiment_service.update_sentiment(
                conversation_id, updated_sentiment
            )

            yield f"data: {json.dumps({'complete': True})}\n\n"

        except LlmResponseException as e:
            full_response = (
                "I'm sorry, I encountered an error and was unable to respond."
            )
            add_event_context(error_type="LlmResponseException", error_message=str(e))
            yield f"data: {json.dumps({'error': full_response})}\n\n"

        finally:
            await self.save_ai_message(
                user_id=user_id, conversation_id=conversation_id, content=full_response
            )
