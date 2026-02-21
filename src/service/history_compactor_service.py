"""
Service to compact conversation history
by summarizing older messages and keeping only the most recent.
reduces token usage while preserving context
Project StakeHolder
"""

import os

from pydantic_ai import (
    Agent,
    ModelRequest,
    ModelResponse,
    ModelMessage,
    TextPart,
    UserPromptPart,
)
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from src.schemas.message_model import Message, MessageType


# Read LLM credentials and config from environment
api_base_url = os.environ.get("AI_PROVIDER_BASE_URL", "")
api_key = os.environ.get("AI_PROVIDER_API_KEY", "")
main_model_name = os.environ.get("AI_PROVIDER_MODEL", "llama3.1:8b")

provider = OpenAIProvider(
    base_url=api_base_url,
    api_key=api_key,
)

summarize_model = OpenAIChatModel(
    model_name=main_model_name,
    provider=provider,
)

# Use less expensive (by token count) model to summarize old messages.
summarize_agent = Agent(
    model=summarize_model,
    instructions="""
        Summarize this conversation, focus on key points and decisions, and keep it concise. 
        Try to remember personal details and preferences mentioned. 
        The summary should capture the essence of the conversation so far,
        without needing to include every message. The summary will be used to provide context for future messages
        """,
)


class HistoryCompactorService:
    """Service for compacting and converting conversation history."""

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

    @staticmethod
    async def summarize_old_messages(
        messages: list[Message],
    ) -> list[ModelMessage]:
        """Summarize old messages while keeping the 10 most recent.
        Uses summarize_agent model."""
        converted_messages = HistoryCompactorService._convert_to_modellist(messages)
        message_cutoff = 10
        if len(messages) >= message_cutoff:
            recent_messages = converted_messages[-message_cutoff:]
            old_messages = converted_messages[:-message_cutoff]

            # Call summarize_agent with list of ModelMessages
            summary = await summarize_agent.run(message_history=old_messages)
            return summary.new_messages() + recent_messages
        return converted_messages
