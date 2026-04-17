"""
AgentService: Main service for agentic AI stakeholder simulation.
This service will orchestrate conversation flow,
persistence, persona, project context, and LLM interaction for a project stakeholder agent.
"""

import json
from datetime import datetime
from typing import AsyncGenerator
from pydantic_ai import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    TextPart,
    UserPromptPart,
)
from pydantic import ValidationError
from src.middlewares.events import add_event_context, wide_event
from src.schemas.message_model import Message
from src.schemas.persona_model import Persona
from src.schemas.project_model import Project
from src.schemas.sentiment_scale_model import SentimentScale
from src.schemas.listening_cues_model import ListeningCues
from src.schemas.instructions_model import InstructionsModel
from src.service.history_message_adapter import convert_messages_to_model_messages
from src.service.model_service import ModelService
from src.service.message_service import MessageService
from src.service.sentiment_service import SentimentService
from src.service.summary_service import SummaryService
from src.agents.stakeholder_agent import (
    AgentResponse,
    run_stakeholder_query_stream as _run_stakeholder_query_stream,
)


class AgentService:
    """Service for orchestrating agent conversations and context."""

    def __init__(
        self,
        model_service: ModelService,
        message_service: MessageService,
        sentiment_service: SentimentService,
        summary_service: SummaryService,
    ) -> None:
        self.model_service: ModelService = model_service
        self.message_service: MessageService = message_service
        self.sentiment_service: SentimentService = sentiment_service
        self.summary_service: SummaryService = summary_service

    def load_persona(self) -> Persona:
        """loads persona model from model service"""
        result = self.model_service.get_model("persona", Persona)
        add_event_context(persona_name=result.name)
        return result

    def load_project(self) -> Project:
        """loads project model from model service"""
        result = self.model_service.get_model("project", Project)
        add_event_context(project_name=result.project_name)
        return result

    def load_sentiment_scale(self) -> SentimentScale:
        """loads sentiment_scale model from model service"""
        return self.model_service.get_model("sentiment_scale", SentimentScale)

    def load_listening_cues(self) -> ListeningCues:
        """loads listening_cues model from model service"""
        return self.model_service.get_model("listening_cues", ListeningCues)

    def load_instructions(self) -> InstructionsModel:
        """loads instructions model from model service"""
        return self.model_service.get_model("instructions", InstructionsModel)

    async def load_history(
        self,
        user_id: str,
        conversation_id: str,
        after: datetime | None = None,
    ) -> list[Message]:
        """loads from message service"""
        if after is not None:
            db_messages = await self.message_service.get_messages_after(
                conversation_id=conversation_id, after=after
            )
        else:
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

    @wide_event("save_user_message")
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

    @wide_event("save_ai_message")
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

    @wide_event("run_stakeholder_query_stream")
    async def run_stakeholder_query_stream(
        self,
        content: str,
        recent_history: list[Message],
        persona: Persona,
        summary_text: str | None = None,
    ) -> AsyncGenerator[AgentResponse, None]:
        """Load context, assemble history from summary + recent messages, and stream."""
        project = self.load_project()
        sentiment_scale = self.load_sentiment_scale()
        listening_cues = self.load_listening_cues()
        instructions = self.load_instructions()

        history: list[ModelMessage] = []
        if summary_text:
            history.append(
                ModelRequest(
                    parts=[UserPromptPart(content="Summarize our conversation so far.")]
                )
            )
            history.append(ModelResponse(parts=[TextPart(content=summary_text)]))
        history += convert_messages_to_model_messages(recent_history)

        async for chunk in _run_stakeholder_query_stream(
            message=content,
            persona=persona,
            project=project,
            history=history,
            sentiment_scale=sentiment_scale,
            listening_cues=listening_cues,
            instructions=instructions,
        ):
            yield chunk

    @wide_event("process_agent_query_stream")
    async def process_agent_query_stream(
        self,
        user_id: str,
        conversation_id: str,
        content: str,
    ) -> AsyncGenerator[str, None]:
        """Stream agent response maintaining architectural consistency, with robust error handling for history loading."""

        summary = await self.summary_service.get_conversation_summary(conversation_id)
        after = (
            summary.window_start
            if summary and summary.window_start and summary.content
            else None
        )

        history = await self.load_history(
            user_id=user_id,
            conversation_id=conversation_id,
            after=after,
        )

        await self.save_user_message(
            user_id=user_id,
            conversation_id=conversation_id,
            content=content,
        )

        persona_with_sentiment = (
            await self.sentiment_service.get_persona_w_current_sentiment(
                conversation_id=conversation_id,
            )
        )

        full_response = ""
        last_sentiment = 0.00
        stream_terminal_state = "cancelled"
        try:
            async for chunk in self.run_stakeholder_query_stream(
                content=content,
                recent_history=history,
                persona=persona_with_sentiment,
                summary_text=summary.content if summary else None,
            ):
                if chunk.sentiment is not None:
                    last_sentiment = chunk.sentiment
                if chunk.content:
                    full_response += chunk.content
                    yield f"data: {json.dumps({'content': chunk.content, 'partial': True})}\n\n"

            add_event_context(ai_response_length=len(full_response))
            yield f"data: {json.dumps({'content': full_response, 'complete': True})}\n\n"
            stream_terminal_state = "completed"

        except Exception as e:
            full_response = "I'm sorry, I encountered an unexpected error and was unable to respond."
            add_event_context(
                error_type=type(e).__name__,
                error_message=str(e.__cause__) if e.__cause__ else str(e),
            )
            yield f"data: {json.dumps({'content': full_response, 'error': True, 'complete': True})}\n\n"
            stream_terminal_state = "errored"

        finally:
            add_event_context(
                stream_terminal_state=stream_terminal_state,
                persisted_response_length=len(full_response),
            )
            for action in (
                self.save_ai_message(
                    user_id=user_id,
                    conversation_id=conversation_id,
                    content=full_response,
                ),
                self.sentiment_service.update_sentiment(
                    conversation_id=conversation_id,
                    new_value=last_sentiment,
                ),
            ):
                try:
                    await action
                except Exception as e:
                    add_event_context(
                        error_type=type(e).__name__,
                        error_message=str(e.__cause__) if e.__cause__ else str(e),
                    )
