"""
Service to compact conversation history
by summarizing older messages and keeping only the most recent.
reduces token usage while preserving context
Project StakeHolder
"""
import os
import uuid
from typing import cast

from pydantic_ai import Agent, ModelRequest, ModelResponse, TextPart, UserPromptPart
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
summarize_agent = Agent[list[str], str](
    model=summarize_model,
    instructions="""
        Summarize this conversation, omitting small talk and unrelated topics.
        Focus on system requirements and important details.
        """
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
        if len(messages) > message_cutoff:
            old_messages = messages[:-message_cutoff]
            recent_messages = messages[-message_cutoff:]
            # Convert old messages to list of strings
            old_message_strings = HistoryCompactorService._messages_to_string_list(
                HistoryCompactorService._convert_to_modellist(old_messages)
            )
            # Call summarize_agent with list of strings
            summary = await summarize_agent.run(old_message_strings)
            # Wrap summary as ModelResponse
            summary_response = ModelResponse(parts=[TextPart(content=summary.output)])
            # Convert recent messages to ModelRequest | ModelResponse
            recent_model_messages = HistoryCompactorService._convert_to_modellist(recent_messages)
            return [summary_response] + recent_model_messages
        else:
            return HistoryCompactorService._convert_to_modellist(messages)



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
                    raise ValueError("Invalid conversation_id")
                if not message_id or (isinstance(message_id, str) and not uuid.UUID(message_id)):
                    raise ValueError("Invalid message_id")
            except ValueError:
                # IDs not needed for summarization,
                # use dummy UUIDs to satisfy type requirement without errors
                dummy_id = uuid.UUID("00000000-0000-0000-0000-000000000DUM")
                conversation_id =  dummy_id
                message_id = dummy_id
            if isinstance(msg, ModelRequest):
                for part in msg.parts:
                    if isinstance(part, UserPromptPart):
                        content = part.content
                        if not isinstance(content, str):
                            content = str(content)
                        msg_list.append(Message(
                            id=message_id,
                            conversation_id=conversation_id,
                            type=RoleEnum.user,
                            content=content
                        ))
            elif isinstance(msg, ModelResponse):
                for part in msg.parts:
                    if isinstance(part, TextPart):
                        content = part.content
                        if not isinstance(content, str):
                            content = str(content)
                        msg_list.append(Message(
                            id=message_id,
                            conversation_id=conversation_id,
                            type=RoleEnum.ai,
                            content=content
                        ))
            else:
                continue

        return await HistoryCompactorService.summarize_old_messages(msg_list)

    @staticmethod
    def _messages_to_string_list(messages: list[ModelRequest | ModelResponse]) -> list[str]:
        """Convert a list of ModelRequest | ModelResponse to a list of their contents as strings."""
        contents = []
        for msg in messages:
            if isinstance(msg, ModelRequest):
                for part in msg.parts:
                    if isinstance(part, UserPromptPart):
                        user_part = cast(UserPromptPart, part)
                        contents.append(str(user_part.content))
            elif isinstance(msg, ModelResponse):
                for part in msg.parts:
                    if isinstance(part, TextPart):
                        text_part = cast(TextPart, part)
                        contents.append(str(text_part.content))
        return contents
