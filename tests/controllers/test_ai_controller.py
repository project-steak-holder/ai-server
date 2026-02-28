"""Unit tests for AI controller."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from src.controllers.ai_controller import generate
from src.schemas.ai import GenerateRequest, GenerateResponse, MessageType
from src.dependencies.user import AuthenticatedUser


@pytest.mark.anyio
async def test_ai_controller_generate_success_and_error():
    payload = GenerateRequest(conversation_id="conv-1", content="hello world")
    current_user = AuthenticatedUser(user_id="user-1")
    wide_event = MagicMock()
    agent_service = MagicMock()
    agent_service.process_agent_query = AsyncMock(
        return_value={"status": "success", "response": "hi"}
    )

    result = await generate(payload, current_user, wide_event, agent_service, None)

    assert isinstance(result, GenerateResponse)
    assert result.content == "hi"
    assert result.type is MessageType.ai
    assert wide_event.add_context.call_count == 2

    agent_service.process_agent_query = AsyncMock(
        return_value={"status": "error", "details": "x"}
    )
    with pytest.raises(HTTPException, match="Error processing agent query"):
        await generate(payload, current_user, wide_event, agent_service, None)


@pytest.mark.anyio
async def test_ai_controller_generate_rate_limit_is_a_dependency():
    """Rate limiting is enforced by the FastAPI dependency, not called inside generate.

    The controller does not import or invoke rate_limit itself; enforcement
    happens before generate() is entered.  Passing None for the resolved
    dependency value (which is what Depends(rate_limit) returns after
    enforcement) must not raise any exception.
    """
    payload = GenerateRequest(conversation_id="conv-1", content="hello")
    current_user = AuthenticatedUser(user_id="user-1")
    wide_event = MagicMock()
    agent_service = MagicMock()
    agent_service.process_agent_query = AsyncMock(
        return_value={"status": "success", "response": "ok"}
    )

    result = await generate(payload, current_user, wide_event, agent_service, None)

    assert isinstance(result, GenerateResponse)
