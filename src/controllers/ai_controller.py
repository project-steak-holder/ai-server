"""
AIController is responsible for:
    handling incoming agent query requests from front end with FastAPI
    validating JWT tokens using Neon (auth service injected into FastAPI)
    delegating processing to AgentService
"""

from fastapi import APIRouter

from src.dependencies import WideEvent, CurrentUser, AgentService, RateLimit
from src.schemas.ai import GenerateRequest, GenerateResponse, MessageType


router = APIRouter(prefix="/api/v1", tags=["ai"])


@router.post("/generate", response_model=GenerateResponse)
async def generate(
    payload: GenerateRequest,
    current_user: CurrentUser,
    wide_event: WideEvent,
    agent_service: AgentService,
    _: RateLimit,
) -> GenerateResponse:
    wide_event.add_context(
        user_id=current_user.user_id,
        conversation_id=str(payload.conversation_id),
        user_message_length=len(payload.content),
    )

    ai_service_response = await agent_service.process_agent_query(
        user_id=current_user.user_id,
        conversation_id=payload.conversation_id,
        content=payload.content,
    )

    wide_event.add_context(
        ai_response_length=len(ai_service_response),
    )

    return GenerateResponse(
        conversation_id=payload.conversation_id,
        content=ai_service_response,
        type=MessageType.ai,
    )
