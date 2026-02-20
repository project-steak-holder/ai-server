"""
Service to compact conversation history
by summarizing older messages and keeping only the most recent.
reduces token usage while preserving context
Project StakeHolder
"""
import os
import uuid

from pydantic_ai import Agent, ModelRequest, ModelResponse, TextPart, UserPromptPart
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from src.agents.stakeholder_agent import AgentDependencies, AgentResponse
from src.schemas.message_model import Message, RoleEnum
from src.exceptions.invalid_message_id_exception import InvalidMessageIdException

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
summarize_agent = Agent[AgentDependencies, AgentResponse](
    model=summarize_model,
    instructions="""
Summarize this conversation, omitting small talk and unrelated topics.
Focus on system requirements and important details.
""",
)

class HistoryCompactorService:
    """Service for compacting and converting conversation history."""


    @staticmethod
    def _convert_to_modellist(messages: list[Message]) -> list[ModelRequest | ModelResponse]:
        """Convert list of Message models to list of ModelMessages."""
        result: list[ModelRequest | ModelResponse] = []
        for msg in messages:
            if msg.role == RoleEnum.user:
                result.append(ModelRequest(parts=[UserPromptPart(content=msg.content)]))
            else:
                result.append(ModelResponse(parts=[TextPart(content=msg.content)]))
        return result



    @staticmethod
    async def summarize_old_messages(messages: list[Message]) -> list[ModelRequest | ModelResponse]:
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
                return summary.all_messages() + recent_messages
            else:
                return recent_messages
        return model_list

    @staticmethod
    async def summarize_processor(messages: list[ModelRequest | ModelResponse]) -> list[ModelRequest | ModelResponse]:
        """
        Adapter for agent history_processors.
        Converts ModelRequest/ModelResponse to Message, summarizes, and returns ModelRequest/ModelResponse.
        """
        msg_list = []
        for msg in messages:
            # You may need to extract conversation_id and id from msg if available
            conversation_id = getattr(msg, "conversation_id", None)
            message_id = getattr(msg, "id", None)
            try:
                if isinstance(conversation_id, str):
                    conversation_id = uuid.UUID(conversation_id)
                elif not isinstance(conversation_id, uuid.UUID):
                    raise InvalidMessageIdException("Invalid conversation_id")
                if not message_id or (isinstance(message_id, str) and not uuid.UUID(message_id)):
                    raise InvalidMessageIdException("Invalid message_id")
            except InvalidMessageIdException:
                # IDs not needed for summarization,
                # use dummy UUIDs to satisfy type requirement without errors
                dummy_id = uuid.UUID("00000000-0000-0000-0000-000000000DUM")
                conversation_id =  dummy_id
                message_id = dummy_id
            if isinstance(msg, ModelRequest):
                if msg.parts and isinstance(msg.parts[0], UserPromptPart):
                    part = msg.parts[0]
                    content = part.content
                    if not isinstance(content, str):
                        content = str(content)
                    msg_list.append(Message(
                        id=message_id,
                        conversation_id=conversation_id,
                        role=RoleEnum.user,
                        content=content
                    ))
                else:
                    continue
            elif isinstance(msg, ModelResponse):
                if msg.parts and isinstance(msg.parts[0], TextPart):
                    text_part = msg.parts[0]
                    content = text_part.content
                    if not isinstance(content, str):
                        content = str(content)
                    msg_list.append(Message(
                        id=message_id,
                        conversation_id=conversation_id,
                        role=RoleEnum.ai,
                        content=content
                    ))
                else:
                    continue
            else:
                continue

        return await HistoryCompactorService.summarize_old_messages(msg_list)



# instantiate Agent with summarize_model and the history processor
# to summarize old (keeps most recent) messages
agent: Agent[AgentDependencies, AgentResponse] = Agent[AgentDependencies, AgentResponse](
       summarize_model,
       history_processors=[HistoryCompactorService.summarize_processor]
   )
