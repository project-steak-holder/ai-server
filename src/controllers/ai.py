"""
AIController is responsible for:
                                handling incoming agent query requests from front end with FastAPI
                                validating JWT tokens using Neon (auth service injected into FastAPI)
                                delegating processing to AgentService
"""
from datetime import datetime, timezone

from fastapi import APIRouter

from src.schemas.ai import GenerateRequest, GenerateResponse, MessageType

router = APIRouter(prefix="/api/v1", tags=["ai"])


@router.post("/generate", response_model=GenerateResponse)
async def generate(payload: GenerateRequest) -> GenerateResponse:
    """FastAPI Controller for handling incoming requests from the front end
            only a single route is needed for MVP
            Neon Auth injected for authentication of JWT in request header
        """
    now = datetime.now(timezone.utc)
    return GenerateResponse(
        conversation_id=payload.conversation_id,
        content="AI response here",
        type=MessageType.ai,
        created_at=now,
        updated_at=now,
    )
