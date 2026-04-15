"""
Service to compact conversation history
by summarizing messages and returning a concise summary.
Runs inside background tasks — no request context available.
Project StakeHolder
"""

import os
from pydantic_ai import (
    Agent,
    ModelMessage,
)

from pydantic_ai.models.google import GoogleModel
from pydantic_ai.providers.google import GoogleProvider

from src.schemas.message_model import Message
from src.service.history_message_adapter import convert_messages_to_model_messages


class HistoryCompactorService:
    """Summarizes conversation messages via LLM."""

    def __init__(self):
        api_key = os.environ.get("AI_PROVIDER_API_KEY", "")
        model_name = os.environ.get("AI_PROVIDER_MODEL", "gemini-2.5-flash")
        self.summarize_model = GoogleModel(
            model_name=model_name,
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
    def estimate_tokens(content: str) -> int:
        """Estimate token count from content string. ~4 chars per token."""
        return len(content) // 4

    async def summarize(self, messages: list[Message]) -> str:
        """Summarize a list of messages. Returns summary text."""
        converted: list[ModelMessage] = convert_messages_to_model_messages(messages)
        result = await self.summarize_agent.run(message_history=converted)
        return result.output
