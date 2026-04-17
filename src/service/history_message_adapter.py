from pydantic_ai import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    TextPart,
    UserPromptPart,
)

from src.schemas.message_model import Message, MessageType


def convert_messages_to_model_messages(messages: list[Message]) -> list[ModelMessage]:
    result: list[ModelMessage] = []
    for msg in messages:
        if msg.role == MessageType.USER:
            result.append(ModelRequest(parts=[UserPromptPart(content=msg.content)]))
        else:
            result.append(ModelResponse(parts=[TextPart(content=msg.content)]))
    return result
