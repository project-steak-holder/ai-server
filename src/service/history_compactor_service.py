"""
Service to compact conversation history
by summarizing older messages and keeping only the most recent.
reduces token usage while preserving context
Project StakeHolder
"""
import os
from pydantic_ai import Agent, ModelMessage
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from src.schemas.message_model import Message

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
Summarize this conversation, omitting small talk and unrelated topics.
Focus on system requirements and important details.
""",
)

class HistoryCompactorService:
    """Service for compacting and converting conversation history."""

    @staticmethod
    def convert_to_dictlist(messages: list[Message]) -> list[dict]:
        """ Convert list of custom Message models
            to list of dicts for LLM use."""
        return [msg.model_dump() for msg in messages]


    @staticmethod
    async def summarize_old_messages(messages: list[Message]) -> list[dict]:
        """Summarize old messages while keeping the 10 most recent.
            Uses summarize_agent model."""
        # Convert to dict list for summarization
        message_dict_list = HistoryCompactorService.convert_to_dictlist(messages)
        # Summarize all but the 10 most recent messages
        if len(message_dict_list) > 10:
            # Summarize all except the 10 most recent
            old_messages = message_dict_list[:-10]
            recent_messages = message_dict_list[-10:]
            if old_messages:
                summary = await summarize_agent.run(message_history=old_messages)
                # Return the summary (as new dict) plus the 10 most recent
                return summary.new_messages() + recent_messages
            else:
                return recent_messages
        return message_dict_list

# instantiate Agent with summarize_model and the history processor
# to summarize old (keeps 10 most recent) messages
agent = Agent(summarize_model, history_processors=[HistoryCompactorService.summarize_old_messages])
