"""Unit tests for AI request/response schemas."""

from src.schemas.ai import GenerateRequest, GenerateResponse, MessageType


def test_ai_schema_models():
    payload = GenerateRequest(conversation_id="conv-1", content="hello")
    response = GenerateResponse(
        conversation_id="conv-1",
        content="hi",
        type=MessageType.ai,
    )

    assert payload.conversation_id == "conv-1"
    assert response.type is MessageType.ai
    assert MessageType.user.value == "user"
