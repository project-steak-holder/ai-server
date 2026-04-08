"""
Service to compact conversation history
by summarizing older messages and keeping only the most recent.
reduces token usage while preserving context
Project StakeHolder
"""

import os
import time
from pydantic_ai import (
    Agent,
    ModelRequest,
    ModelResponse,
    ModelMessage,
    TextPart,
    UserPromptPart,
)

from pydantic_ai.models.google import GoogleModel
from pydantic_ai.providers.google import GoogleProvider

from src.middlewares.events import add_event_context, wide_event
from src.schemas.message_model import Message, MessageType


class HistoryCompactorService:
    """Service for compacting and converting conversation history."""

    def __init__(self):
        api_key = os.environ.get("GOOGLE_API_KEY", "")
        main_model_name = os.environ.get("AI_PROVIDER_MODEL", "gemini-2.5-flash")
        self.summarize_model = GoogleModel(
            model_name=main_model_name,
            provider=GoogleProvider(api_key=api_key),
        )
        self.summarize_agent = Agent(
            model=self.summarize_model,
            instructions="""
                Summarize this conversation, focus on key points and decisions, and keep it concise. 
                Try to remember personal details and preferences mentioned. 
                The summary should capture the essence of the conversation so far,
                without needing to include every message. The summary will be used to provide context for future messages
                """,
        )

    @staticmethod
    def _convert_to_modellist(
        messages: list[Message],
    ) -> list[ModelMessage]:
        """Convert list of Message models to list of ModelMessages."""
        result: list[ModelMessage] = []
        for msg in messages:
            if msg.role == MessageType.USER:
                result.append(ModelRequest(parts=[UserPromptPart(content=msg.content)]))
            else:
                result.append(ModelResponse(parts=[TextPart(content=msg.content)]))
        return result

    @wide_event("summarize_old_messages")
    async def summarize_old_messages(
        self,
        messages: list[Message],
    ) -> list[ModelMessage]:
        """Summarize old messages while keeping the 10 most recent.
        Uses summarize_agent model."""
        converted_messages = self._convert_to_modellist(messages)
        message_cutoff = 10
        if len(messages) >= message_cutoff:
            recent_messages = converted_messages[-message_cutoff:]
            old_messages = converted_messages[:-message_cutoff]
            start = time.time()
            # Call summarize_agent with list of ModelMessages
            summary = await self.summarize_agent.run(message_history=old_messages)
            end = time.time()
            add_event_context(
                summary_latency_ms=int((end - start) * 1000),
                original_message_count=len(messages),
                summary_message_count=len(summary.new_messages()),
            )
            return summary.new_messages() + recent_messages
        return converted_messages
