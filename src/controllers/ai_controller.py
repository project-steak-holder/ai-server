"""
AIController is responsible for:
    handling incoming agent query requests from front end with FastAPI
    validating JWT tokens using Neon (auth service injected into FastAPI)
    delegating processing to AgentService
"""

from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException

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
    start_time = datetime.now(timezone.utc)
    wide_event.add_context(
        user_id=current_user.user_id,
        conversation_id=str(payload.conversation_id),
        user_message_preview=payload.content[:50],
        user_message_length=len(payload.content),
        ai_service_process_message_status="started",
        ai_service_start_time=start_time.isoformat(),
    )

    ai_service_response = await agent_service.process_agent_query(
        user_id=current_user.user_id,
        conversation_id=payload.conversation_id,
        content=payload.content,
    )

    end_time = datetime.now(timezone.utc)
    duration_ms = int((end_time - start_time).total_seconds() * 1000)

    wide_event.add_context(
        ai_service_process_message_status=ai_service_response.get("status", "unknown"),
        ai_service_response_preview=ai_service_response.get("response", "")[:50],
        ai_service_response_length=len(ai_service_response.get("response", "")),
        ai_service_response_error_details=ai_service_response.get("details", ""),
        ai_service_end_time=end_time.isoformat(),
        ai_service_duration_time_ms=duration_ms,
    )

    if ai_service_response.get("status") == "error":
        raise HTTPException(status_code=500, detail="Error processing agent query")

    return GenerateResponse(
        conversation_id=payload.conversation_id,
        content=ai_service_response.get("response", ""),
        type=MessageType.ai,
    )
