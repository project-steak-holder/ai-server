"""
Service to compact conversation history
by summarizing older messages and keeping only the most recent.
reduces token usage while preserving context
Project StakeHolder
"""
import os
from pydantic_ai import Agent, ModelMessage, ModelRequest, ModelResponse, TextPart, UserPromptPart
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from src.schemas.message_model import Message, RoleEnum

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
    def _convert_to_modellist(messages: list[Message]) -> list[ModelMessage]:
        """Convert list of Message models to list of ModelMessages."""
        result = []
        for msg in messages:
            if msg.role == RoleEnum.user:
                result.append(ModelRequest(parts=[UserPromptPart(content=msg.content)]))
            else:
                result.append(ModelResponse(parts=[TextPart(content=msg.content)]))
        return result



    @staticmethod
    async def summarize_old_messages(messages: list[Message]) -> list[ModelMessage]:
        """Summarize old messages while keeping the 10 most recent.
            Uses summarize_agent model."""
        message_cutoff = 10
        # Convert to dict list for summarization
        model_list = HistoryCompactorService._convert_to_modellist(messages)
        # Summarize all but the (message_cutoff) most recent messages
        if len(model_list) > message_cutoff:
            # Summarize all except the (message_cutoff) most recent
            old_messages = model_list[:-message_cutoff]
            recent_messages = model_list[-message_cutoff:]
            if old_messages:
                summary = await summarize_agent.run(message_history=old_messages)
                # Return the summary plus the (message_cutoff) most recent
                return summary + recent_messages
            else:
                return recent_messages
        return model_list

# instantiate Agent with summarize_model and the history processor
# to summarize old (keeps most recent) messages
agent = Agent(summarize_model, history_processors=[HistoryCompactorService.summarize_old_messages])
