"""
AIController is responsible for:
    handling incoming agent query requests from front end with FastAPI
    validating JWT tokens using Neon (auth service injected into FastAPI)
    delegating processing to AgentService
"""

import datetime
from fastapi import APIRouter

from src.dependencies import WideEvent, CurrentUser, AgentService
from src.schemas.ai import GenerateRequest, GenerateResponse, MessageType


router = APIRouter(prefix="/api/v1", tags=["ai"])


@router.post("/generate", response_model=GenerateResponse)
async def generate(
    payload: GenerateRequest,
    current_user: CurrentUser,
    wide_event: WideEvent,
    agent_service: AgentService,
) -> GenerateResponse:
    """FastAPI Controller for handling incoming requests from the front end
    only a single route is needed for MVP
    Neon Auth injected for authentication of JWT in request header
    """
    wide_event.add_context(
        user_id=current_user.user_id,
        conversation_id=str(payload.conversation_id),
    )

    ai_service_response = await agent_service.process_agent_query(
        user_id=current_user.user_id,
        conversation_id=payload.conversation_id,
        content=payload.content,
    )

    wide_event.add_context(
        **ai_service_response.get("event", {})
    )  # Add AI response to event context for logging

    return GenerateResponse(
        conversation_id=payload.conversation_id,
        content=ai_service_response.get("response", ""),
        type=MessageType.ai,
        created_at=datetime.datetime.utcnow(),
        updated_at=datetime.datetime.utcnow(),
    )
